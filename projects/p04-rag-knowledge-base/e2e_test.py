"""
端到端验证脚本：导入文档 → 提问 → 获取带溯源的答案。
用法：uv run python e2e_test.py
输出同时写入 _evidence/p04/e2e_test.log
"""
from __future__ import annotations
import os
import sys
import uuid
import time
import logging
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# mock vertexai 防止 ragas 导入崩溃（即使本脚本不直接用 ragas，保持环境一致）
if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()

os.environ.setdefault("MONGO_HISTORY_ENABLED", "false")

from processor.import_processor.main_graph import KBImportWorkflow
from processor.import_processor.base import setup_logging
from processor.query_processor.main_graph import query_app
from processor.query_processor.state import create_default_state
from utils.reranker_http_utils import get_last_rerank_status

REPO_ROOT = PROJECT_ROOT.parent.parent
EVIDENCE_DIR = REPO_ROOT / "_evidence" / "p04"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = EVIDENCE_DIR / "e2e_test.log"

DOC_PATH = str(PROJECT_ROOT / "eval" / "hak180产品安全手册_new.md")
TEST_QUESTION = "hak 180 烫金机：为什么不建议把设备放在加热器、空调、电风扇或水附近？"
TEST_QUESTION_2 = "hak 180 烫金机：附近有起搏器的用户应该注意什么？"


_DISAMBIGUATION_PATTERNS = [
    "您是想问", "以下哪个产品", "请问您指的是", "您指的是哪个",
    "请选择", "以下哪一款", "请确认您",
]


def is_disambiguation(answer: str) -> bool:
    """检测答案是否为消歧问句（而非实质性回答）"""
    return any(pat in answer for pat in _DISAMBIGUATION_PATTERNS)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("e2e_test")


def phase_1_import() -> dict:
    """
    阶段一：导入文档到知识库。
    :return: {"chunk_count": int, "elapsed_seconds": float}
    """
    logger.info("=" * 60)
    logger.info("阶段一：文档导入")
    logger.info("=" * 60)
    logger.info(f"文档路径: {DOC_PATH}")

    if not Path(DOC_PATH).exists():
        raise FileNotFoundError(f"测试文档不存在: {DOC_PATH}")

    task_id = str(uuid.uuid4())
    file_dir = str(PROJECT_ROOT / "temp-files" / "e2e_test")
    os.makedirs(file_dir, exist_ok=True)

    init_state = {
        "task_id": task_id,
        "file_dir": file_dir,
        "import_file_path": DOC_PATH,
    }

    logger.info(f"task_id: {task_id}")
    t0 = time.time()
    workflow = KBImportWorkflow()
    final_state = workflow.run(init_state)
    elapsed = time.time() - t0

    chunk_count = len(final_state.get("chunks", []))
    item_name = final_state.get("item_name", "")
    file_title = final_state.get("file_title", "")

    logger.info(f"导入完成！耗时: {elapsed:.1f}s")
    logger.info(f"文件标题: {file_title}")
    logger.info(f"识别主体: {item_name}")
    logger.info(f"切片数量: {chunk_count}")

    return {
        "task_id": task_id,
        "chunk_count": chunk_count,
        "item_name": item_name,
        "file_title": file_title,
        "elapsed_seconds": round(elapsed, 1),
    }


def phase_2_query(question: str, label: str = "") -> dict:
    """
    阶段二：对知识库提问，获取带溯源的答案。
    :param question: 问题文本
    :param label: 日志标签
    :return: {"answer": str, "sources": list, "rerank_backend": str, "elapsed_seconds": float}
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"阶段二：知识问答{f' ({label})' if label else ''}")
    logger.info("=" * 60)
    logger.info(f"问题: {question}")

    session_id = f"e2e-test-{uuid.uuid4().hex}"
    message_id = f"e2e-msg-{uuid.uuid4().hex}"

    state = create_default_state(
        original_query=question,
        session_id=session_id,
        message_id=message_id,
        is_stream=False,
    )

    t0 = time.time()
    final_state = query_app.invoke(state)
    elapsed = time.time() - t0

    answer = str(final_state.get("answer", "")).strip()
    reranked_docs = final_state.get("reranked_docs", [])
    rerank_status = get_last_rerank_status()

    logger.info(f"回答耗时: {elapsed:.1f}s")
    logger.info(f"Rerank 实际后端: {rerank_status['backend']}")
    if rerank_status.get("degrade_reason"):
        logger.info(f"降级原因: {rerank_status['degrade_reason']}")
    logger.info(f"召回文档数: {len(reranked_docs)}")
    logger.info(f"答案: {answer[:200]}{'...' if len(answer) > 200 else ''}")

    sources = []
    for i, doc in enumerate(reranked_docs, 1):
        content = doc.get("content", "")[:100]
        source = doc.get("source", "unknown")
        score = doc.get("score", "N/A")
        logger.info(f"  Top-{i} [score={score}, source={source}]: {content}...")
        sources.append({
            "rank": i,
            "score": score,
            "source": source,
            "content_preview": content,
        })

    return {
        "answer": answer,
        "sources": sources,
        "rerank_backend": rerank_status["backend"],
        "elapsed_seconds": round(elapsed, 1),
    }


def main():
    """运行端到端验证：导入 → 问答。"""
    logger.info("P04 RAG 知识库 端到端验证")
    logger.info(f"文档: {DOC_PATH}")
    logger.info(f"RERANK_BACKEND: {os.getenv('RERANK_BACKEND', '未设置')}")
    logger.info("")

    import_result = phase_1_import()

    query_result_1 = phase_2_query(TEST_QUESTION, "问题1")
    query_result_2 = phase_2_query(TEST_QUESTION_2, "问题2")

    logger.info("")
    logger.info("=" * 60)
    logger.info("端到端验证汇总")
    logger.info("=" * 60)
    logger.info(f"导入: {import_result['chunk_count']} chunks, "
                f"耗时 {import_result['elapsed_seconds']}s")
    logger.info(f"问题1: rerank={query_result_1['rerank_backend']}, "
                f"sources={len(query_result_1['sources'])}, "
                f"耗时 {query_result_1['elapsed_seconds']}s")
    logger.info(f"问题2: rerank={query_result_2['rerank_backend']}, "
                f"sources={len(query_result_2['sources'])}, "
                f"耗时 {query_result_2['elapsed_seconds']}s")

    all_pass = (
        import_result["chunk_count"] > 0
        and bool(query_result_1["answer"])
        and len(query_result_1["sources"]) > 0
        and not is_disambiguation(query_result_1["answer"])
        and bool(query_result_2["answer"])
        and len(query_result_2["sources"]) > 0
        and not is_disambiguation(query_result_2["answer"])
    )
    logger.info(f"结论: {'全部通过' if all_pass else '存在失败项'}")

    result_summary = {
        "import": import_result,
        "query_1": query_result_1,
        "query_2": query_result_2,
        "all_pass": all_pass,
    }

    import json
    summary_file = EVIDENCE_DIR / "e2e_result.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(result_summary, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存: {summary_file}")


if __name__ == "__main__":
    main()
