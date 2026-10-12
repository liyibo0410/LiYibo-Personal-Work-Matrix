# _evidence/p04/probe_rerank_models_p1.py
# 列出 Token Plan 端点的全部模型，找出 rerank / embedding 相关模型名，并逐个实测

from __future__ import annotations

import os
import sys
import json
import io
from pathlib import Path

ROOT = r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
KEY = os.getenv("MCP_API_KEY", "")

import httpx

TP_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行，请各部门报名。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
]

# ── 1. 列出全部模型 ──
with httpx.Client(timeout=40) as c:
    r = c.get(f"{TP_BASE}/models", headers=H)
data = r.json().get("data", [])
ids = sorted({m.get("id", "") for m in data})
print(f"[1] Token Plan 共 {len(ids)} 个模型：")
for i in ids:
    print(f"    {i}")

cand = [i for i in ids if ("rerank" in i.lower() or "rank" in i.lower() or "embed" in i.lower())]
print(f"\n[2] rerank/embedding 候选: {cand}")

# ── 2. 对候选模型逐个试 /rerank ──
print("\n[3] 逐个实测 /rerank：")
out = {}
for m in cand + ["qwen3-rerank", "text-rerank-v1", "gte-rerank"]:
    if m in out:
        continue
    try:
        with httpx.Client(timeout=40) as c:
            rr = c.post(
                f"{TP_BASE}/rerank",
                headers=H,
                json={"model": m, "query": QUERY, "documents": DOCS, "top_n": 3},
            )
        body = rr.text[:220]
        ok = rr.status_code == 200
        print(f"    {m:<28} HTTP {rr.status_code}  {body[:150]}")
        out[m] = {"status": rr.status_code, "body_head": body}
        if ok:
            print(f"      ^^^ 成功！响应: {body[:200]}")
    except Exception as exc:
        print(f"    {m:<28} 异常 {type(exc).__name__}: {exc}")
        out[m] = {"status": None, "error": str(exc)[:150]}

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_rerank_models_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump({"all_models": ids, "rerank_probe": out}, f, ensure_ascii=False, indent=2)
