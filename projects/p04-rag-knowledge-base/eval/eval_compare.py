"""
Local vs Cloud 重排对比评测脚本。

对同一份 qa.csv 测试集，分别用 local（BGE-reranker-large）和 cloud（DashScope TextReRank）
两种重排后端跑 RAG 流程，收集答案与上下文，然后统一用 Ragas 评估，最后输出对比报告。

输出：
  - _evidence/p04/rag_compare_result_local.csv  （local 单条结果）
  - _evidence/p04/rag_compare_result_cloud.csv   （cloud 单条结果）
  - _evidence/p04/rag_compare_report.json        （汇总对比报告）

用法：cd projects/p04-rag-knowledge-base && uv run python eval/eval_compare.py
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()

os.environ.setdefault("MONGO_HISTORY_ENABLED", "false")

import pandas as pd
from datasets import Dataset
from langchain_core.embeddings import Embeddings

from ragas import evaluate
from ragas.metrics._answer_correctness import answer_correctness
from ragas.metrics._answer_relevance import answer_relevancy
from ragas.metrics._context_precision import context_precision
from ragas.metrics._context_recall import context_recall
from ragas.metrics._faithfulness import faithfulness
from ragas.run_config import RunConfig

from utils.embedding_utils import generate_embeddings, get_bge_m3_ef
from utils.llm_utils import get_llm_client
from processor.query_processor.main_graph import query_app
from processor.query_processor.state import create_default_state

EVAL_DIR = PROJECT_ROOT / "eval"
REPO_ROOT = PROJECT_ROOT.parent.parent
EVIDENCE_DIR = REPO_ROOT / "_evidence" / "p04"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = EVAL_DIR / "qa.csv"

METRICS = [faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness]
METRIC_NAMES = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall", "Answer Correctness"]


class BgeM3LangChainEmbeddings(Embeddings):
    """BGE-M3 适配 Ragas 的 LangChain Embeddings 接口。"""
    def __init__(self, model: Any) -> None:
        self.embedding_model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = generate_embeddings(texts)
        if not result:
            raise RuntimeError("BGE-M3 文档向量生成失败")
        return result["dense"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def run_rag_backend(test_df: pd.DataFrame, backend: str) -> tuple[pd.DataFrame, list[dict]]:
    """
    用指定后端跑 RAG 流程，收集答案、上下文和延迟数据。
    :param test_df: 含 question、ground_truth 的 DataFrame
    :param backend: "local" 或 "cloud"
    :return: (rag_df, latency_records)
    """
    os.environ["RERANK_BACKEND"] = backend

    # 重置 reranker 单例，确保切换后端时重新加载
    from utils import reranker_http_utils
    reranker_http_utils._local_reranker = None
    reranker_http_utils._local_reranker_load_error = None

    from config import reranker_config as rc_mod
    rc_mod.reranker_config.backend = backend

    print(f"\n{'='*60}")
    print(f"  RAG 流程 | backend={backend}")
    print(f"{'='*60}")

    # warmup：首次调用含模型加载 / CUDA 初始化，不计入统计
    print("  [warmup] 预热中...")
    warmup_state = create_default_state(
        original_query=test_df.iloc[0]["question"],
        session_id=f"warmup-{backend}-{uuid4().hex}",
        message_id=f"warmup-{uuid4().hex}",
        is_stream=False,
    )
    query_app.invoke(warmup_state)
    print("  [warmup] 完成")

    rag_rows: list[dict[str, Any]] = []
    latency_records: list[dict] = []
    session_id = f"compare-{backend}-{uuid4().hex}"

    for idx, row in enumerate(test_df.itertuples(index=False), start=1):
        question = row.question
        print(f"  [{idx}/{len(test_df)}] {question[:40]}...")

        state = create_default_state(
            original_query=question,
            session_id=session_id,
            message_id=f"compare-{uuid4().hex}",
            is_stream=False,
        )

        t0 = time.time()
        final_state = query_app.invoke(state)
        elapsed = time.time() - t0

        answer = str(final_state.get("answer", "")).strip()
        reranked_docs = final_state.get("reranked_docs", [])
        rerank_status = reranker_http_utils.get_last_rerank_status()

        contexts = []
        for doc in reranked_docs:
            content = str(doc.get("content", "")).strip()
            if content:
                contexts.append(content)

        rag_rows.append({
            "question": question,
            "contexts": contexts,
            "answer": answer,
            "ground_truth": row.ground_truth,
        })

        latency_records.append({
            "question": question[:50],
            "backend": backend,
            "actual_backend": rerank_status["backend"],
            "elapsed_seconds": round(elapsed, 2),
            "source_count": len(contexts),
            "degrade_reason": rerank_status.get("degrade_reason", ""),
        })

        actual = rerank_status["backend"]
        print(f"    → {elapsed:.1f}s | rerank={actual} | sources={len(contexts)}")

    rag_df = pd.DataFrame(rag_rows)
    return rag_df, latency_records


def evaluate_with_ragas(rag_df: pd.DataFrame, label: str) -> dict:
    """
    用 Ragas 评估一组 RAG 结果。
    :param rag_df: 含 question、contexts、answer、ground_truth 的 DataFrame
    :param label: 标签（用于日志）
    :return: 各指标均分的字典
    """
    print(f"\n{'='*60}")
    print(f"  Ragas 评估 | {label}")
    print(f"{'='*60}")

    llm = get_llm_client(json_mode=True)
    if llm is None:
        raise RuntimeError("无法获取评估 LLM")
    bge_ef = get_bge_m3_ef()
    if bge_ef is None:
        raise RuntimeError("无法获取 BGE-M3 模型")
    embeddings = BgeM3LangChainEmbeddings(bge_ef)

    dataset = Dataset.from_dict({
        "question": rag_df["question"].tolist(),
        "contexts": rag_df["contexts"].tolist(),
        "answer": rag_df["answer"].tolist(),
        "ground_truth": rag_df["ground_truth"].tolist(),
    })

    t0 = time.time()
    result = evaluate(
        dataset=dataset,
        metrics=METRICS,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
        run_config=RunConfig(
            timeout=180,
            max_retries=5,
            max_wait=10,
            max_workers=2,
        ),
    )
    elapsed = time.time() - t0
    print(f"  Ragas 评估完成，耗时: {elapsed:.1f}s")

    score_df = result.to_pandas()
    means = {}
    for name in METRIC_NAMES:
        col = name.lower().replace(" ", "_")
        if col in score_df.columns:
            means[name] = round(float(pd.to_numeric(score_df[col], errors="coerce").mean()), 4)
        else:
            means[name] = None
    return means


def main():
    """主流程：加载测试集 → local RAG → cloud RAG → 分别 Ragas 评估 → 输出对比报告。"""
    print("=" * 60)
    print("  P04 RAG 知识库 · Local vs Cloud 重排对比评测")
    print("=" * 60)

    # 步骤1：加载测试集
    print("\n[Step 1] 加载测试集...")
    test_df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
    test_df = test_df.loc[:, ["question", "ground_truth"]].copy()
    test_df["question"] = test_df["question"].astype(str).str.strip()
    test_df["ground_truth"] = test_df["ground_truth"].astype(str).str.strip()
    print(f"  共 {len(test_df)} 条测试问题")

    # 步骤2：Local RAG
    local_df, local_latencies = run_rag_backend(test_df, "local")

    # 保存 local 中间结果
    local_csv = EVIDENCE_DIR / "rag_compare_result_local.csv"
    local_df.to_csv(local_csv, index=False, encoding="utf-8-sig")
    print(f"\n  Local 结果已保存: {local_csv}")

    # 步骤3：Cloud RAG
    cloud_df, cloud_latencies = run_rag_backend(test_df, "cloud")

    cloud_csv = EVIDENCE_DIR / "rag_compare_result_cloud.csv"
    cloud_df.to_csv(cloud_csv, index=False, encoding="utf-8-sig")
    print(f"\n  Cloud 结果已保存: {cloud_csv}")

    # 确定实际后端标签（用于呈现）
    local_actual = local_latencies[0]["actual_backend"] if local_latencies else "unknown"
    cloud_actual = cloud_latencies[0]["actual_backend"] if cloud_latencies else "unknown"

    local_label = f"Local ({local_actual})"
    cloud_label = f"Cloud ({cloud_actual})" if cloud_actual == "cloud" else f"Cloud→{cloud_actual}"

    # 步骤4：Ragas 评估
    local_scores = evaluate_with_ragas(local_df, local_label)
    cloud_scores = evaluate_with_ragas(cloud_df, cloud_label)

    # 步骤5：汇总对比报告
    print(f"\n{'='*60}")
    print("  对比报告")
    print(f"{'='*60}")

    # 降级说明
    degrade_notes = []
    for lat_list, label in [(local_latencies, "local"), (cloud_latencies, "cloud")]:
        for rec in lat_list:
            if rec["actual_backend"] != rec["backend"]:
                degrade_notes.append(
                    f"  {label} 请求 backend={rec['backend']}，"
                    f"实际降级为 {rec['actual_backend']}（{rec.get('degrade_reason', '')}）"
                )
                break

    if degrade_notes:
        print("  ⚠ 降级说明:")
        for note in degrade_notes:
            print(note)
    else:
        print("  所有请求均使用指定后端，无降级")

    latency_df = pd.DataFrame(local_latencies + cloud_latencies)
    latency_csv = EVIDENCE_DIR / "rag_compare_latency.csv"
    latency_df.to_csv(latency_csv, index=False, encoding="utf-8-sig")

    report = {
        "test_set_size": len(test_df),
        "local": {
            "ragas_scores": local_scores,
            "avg_latency_seconds": round(
                sum(r["elapsed_seconds"] for r in local_latencies) / len(local_latencies), 2
            ),
            "actual_backend": local_actual,
        },
        "cloud": {
            "ragas_scores": cloud_scores,
            "avg_latency_seconds": round(
                sum(r["elapsed_seconds"] for r in cloud_latencies) / len(cloud_latencies), 2
            ),
            "actual_backend": cloud_actual,
        },
        "degrade_notes": degrade_notes,
        "latency_details": local_latencies + cloud_latencies,
    }

    report_file = EVIDENCE_DIR / "rag_compare_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  {'指标':<25} {local_label:>20} {cloud_label:>20} {'差值':>10}")
    print(f"  {'-'*75}")
    for metric in METRIC_NAMES:
        l_score = local_scores.get(metric)
        c_score = cloud_scores.get(metric)
        l_str = f"{l_score:.4f}" if l_score is not None else "N/A"
        c_str = f"{c_score:.4f}" if c_score is not None else "N/A"
        diff = ""
        if l_score is not None and c_score is not None:
            d = l_score - c_score
            diff = f"{d:+.4f}"
        print(f"  {metric:<25} {l_str:>20} {c_str:>20} {diff:>10}")

    l_lat = report["local"]["avg_latency_seconds"]
    c_lat = report["cloud"]["avg_latency_seconds"]
    print(f"  {'平均延迟 (秒)':<25} {l_lat:>20.2f} {c_lat:>20.2f} {l_lat - c_lat:>+10.2f}")

    l_net = "是" if local_actual == "cloud" else "否"
    c_net = "是" if cloud_actual == "cloud" else "否"
    print(f"  {'是否出网':<25} {l_net:>20} {c_net:>20}")

    print(f"\n  报告已保存: {report_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
