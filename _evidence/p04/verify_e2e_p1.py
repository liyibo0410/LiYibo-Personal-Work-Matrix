# _evidence/p04/verify_e2e_p1.py
# P1 独立端到端取证 —— 不复用 Qoder 的 e2e_test.py
# 目的：
#   ① 验证 Qoder 报的端到端结果是否可复现
#   ② 【核心】拿到 rerank 前的候选条数 vs 断崖后的条数，证明 D5-01 在真实链路上的影响
#   ③ 验证 query_2 走消歧分支的说法

from __future__ import annotations

import os
import sys
import json
import io
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

ROOT = r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()
os.environ.setdefault("MONGO_HISTORY_ENABLED", "false")

OUT = {}


def log(m):
    print(m, flush=True)


log("=" * 70)
log("P1 独立端到端取证 · P04 RAG（不复用 Qoder 脚本）")
log("=" * 70)

from processor.query_processor.main_graph import query_app
from processor.query_processor.state import create_default_state
from processor.query_processor.nodes.node_rerank import NodeRerank
from utils.reranker_http_utils import (
    rerank_documents,
    get_last_rerank_status,
    reset_local_reranker,
)

Q1 = "hak 180 烫金机：为什么不建议把设备放在加热器、空调、电风扇或水附近？"
Q2 = "HAK180 附近有起搏器的用户应该注意什么？"

node = NodeRerank()


def probe(q, label):
    log("")
    log("-" * 70)
    log(f"{label}: {q}")
    log("-" * 70)
    state = create_default_state(
        original_query=q,
        session_id=f"p1-{uuid.uuid4().hex}",
        message_id=f"p1m-{uuid.uuid4().hex}",
        is_stream=False,
    )
    t0 = time.time()
    fs = query_app.invoke(state)
    elapsed = time.time() - t0

    rrf = fs.get("rrf_chunks") or []
    web = fs.get("web_search_docs") or []
    reranked = fs.get("reranked_docs") or []
    answer = str(fs.get("answer", "")).strip()

    n_before = len(rrf) + len(web)
    n_after = len(reranked)

    log(f"  耗时 {elapsed:.1f}s")
    log(f"  rerank 前候选: rrf_chunks={len(rrf)} + web={len(web)} = {n_before} 条")
    log(f"  断崖后保留   : reranked_docs = {n_after} 条")
    log(f"  ★ 被断崖砍掉 : {n_before - n_after} 条")
    st = get_last_rerank_status()
    log(f"  rerank backend = {st['backend']}  degrade='{st['degrade_reason'][:50]}'")
    log(f"  答案前 150 字: {answer[:150]}")

    # 复算：把 rerank 前的完整候选重新打分，看断崖在哪砍
    merged = [d.get("content") for d in rrf] + [
        (d.get("snippet") or "") for d in web
    ]
    merged = [c for c in merged if c]
    detail = None
    if merged:
        try:
            scores = rerank_documents(q, merged)
            ranked = sorted(
                [{"content": c, "score": s} for c, s in zip(merged, scores)],
                key=lambda x: x["score"],
                reverse=True,
            )
            cut = node._step_3_cliff_cutoff(ranked)
            log(f"  ── 完整分数与断崖位置（共 {len(merged)} 条）──")
            for i, d in enumerate(ranked):
                mark = "保留" if i < len(cut) else "✂ 砍掉"
                log(f"    [{i}] score={d['score']:+.4f} {mark} | {d['content'][:46]}...")
            log(f"  → 断崖保留 {len(cut)} / {len(merged)} 条（RERANK_MIN_TOPK=3 为下限）")
            detail = {
                "before": len(merged),
                "after": len(cut),
                "scores": [round(d["score"], 4) for d in ranked],
                "cut_at": len(cut),
            }
        except Exception as exc:
            log(f"  [!] 复算失败: {exc}")

    return {
        "elapsed": round(elapsed, 1),
        "rrf": len(rrf),
        "web": len(web),
        "before": n_before,
        "after": n_after,
        "cut_count": n_before - n_after,
        "backend": st["backend"],
        "answer_len": len(answer),
        "answer_preview": answer[:200],
        "is_disambiguation": ("请明确" in answer or "想问以下哪个" in answer),
        "cliff_detail": detail,
    }


OUT["query_1"] = probe(Q1, "问题1（带产品名）")
OUT["query_2"] = probe(Q2, "问题2（不带产品名，Qoder 报称走消歧）")

log("")
log("=" * 70)
log("汇总")
log("=" * 70)
for k, v in OUT.items():
    log(
        f"  {k}: 候选 {v['before']} → 保留 {v['after']}（砍 {v['cut_count']} 条）"
        f" | backend={v['backend']} | 消歧={v['is_disambiguation']}"
    )

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_e2e_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(OUT, f, ensure_ascii=False, indent=2)
