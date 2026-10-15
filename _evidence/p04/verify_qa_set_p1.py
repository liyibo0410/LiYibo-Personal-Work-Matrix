# _evidence/p04/verify_qa_set_p1.py
# P1 交付前自检：新造的 36 条评测集能否真正跑通（不走消歧、有答案、有溯源）

from __future__ import annotations

import os
import sys
import json
import io
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

if "langchain_community.chat_models.vertexai" not in sys.modules:
    sys.modules["langchain_community.chat_models.vertexai"] = MagicMock()
os.environ.setdefault("MONGO_HISTORY_ENABLED", "false")

import pandas as pd
from processor.query_processor.main_graph import query_app
from processor.query_processor.state import create_default_state
from utils.reranker_http_utils import get_last_rerank_status

QA = os.path.join(ROOT, "eval", "qa.csv")

df = pd.read_csv(QA, encoding="utf-8-sig")
print(f"[info] 评测集共 {len(df)} 条，列: {list(df.columns)}")

# 抽样：首条、末条、中间一条、以及一条 hard（保修责任）
SAMPLE_IDX = [0, 3, len(df) // 2, len(df) - 3, len(df) - 1]

out = []
for i in SAMPLE_IDX:
    row = df.iloc[i]
    q = str(row["question"]).strip()
    gt = str(row["ground_truth"]).strip()
    print("\n" + "=" * 70)
    print(f"[{i}] {q}")
    print("=" * 70)

    state = create_default_state(
        original_query=q,
        session_id=f"qa-{uuid.uuid4().hex}",
        message_id=f"qam-{uuid.uuid4().hex}",
        is_stream=False,
    )
    t0 = time.time()
    fs = query_app.invoke(state)
    elapsed = time.time() - t0

    answer = str(fs.get("answer", "")).strip()
    docs = fs.get("reranked_docs") or []
    st = get_last_rerank_status()

    is_disamb = ("请明确" in answer or "想问以下哪个" in answer)
    print(f"  耗时 {elapsed:.1f}s | rerank={st['backend']} | 溯源 {len(docs)} 条 | 消歧={is_disamb}")
    print(f"  答案: {answer[:160]}")

    out.append({
        "idx": i,
        "question": q,
        "elapsed": round(elapsed, 1),
        "backend": st["backend"],
        "sources": len(docs),
        "is_disambiguation": is_disamb,
        "answer_len": len(answer),
        "answer": answer[:300],
        "ground_truth": gt[:200],
    })

print("\n" + "=" * 70)
print("汇总")
print("=" * 70)
ok = 0
for r in out:
    good = (not r["is_disambiguation"]) and r["sources"] > 0 and r["answer_len"] > 0
    ok += 1 if good else 0
    print(f"  [{r['idx']:>2}] 溯源{r['sources']} 消歧={str(r['is_disambiguation']):<5} "
          f"答案{str(r['answer_len']):>3}字 -> {'OK' if good else 'FAIL'}")

print(f"\n  可用 {ok}/{len(out)}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_qa_set_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
