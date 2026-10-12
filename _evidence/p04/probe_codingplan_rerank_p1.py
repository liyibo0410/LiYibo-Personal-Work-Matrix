# _evidence/p04/probe_codingplan_rerank_p1.py
# P1 实测：sk-ws- (Coding Plan) Key 能否跑云端 rerank
# 安全：Key 由环境变量 WS_API_KEY 传入，脚本与日志均不落盘 Key 明文

from __future__ import annotations

import os
import sys
import json
import io

KEY = os.environ.get("WS_API_KEY", "")
BASE = "https://ws-amdqcpdtt4gdo5ax.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

print(f"[info] WS_API_KEY: prefix={KEY[:7]!r} len={len(KEY)}  (Key 本身不打印)")
if not KEY:
    print("[!] 未读到环境变量 WS_API_KEY，退出")
    sys.exit(1)

import httpx

H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行，请各部门报名。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
]

out = {}


def probe(name, method, path, body=None, timeout=40):
    url = f"{BASE}{path}"
    print("")
    print("=" * 66)
    print(f"  {name}")
    print(f"  {method} {url}")
    print("=" * 66)
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.get(url, headers=H) if method == "GET" else c.post(url, headers=H, json=body)
        txt = r.text
        print(f"  HTTP {r.status_code}")
        print(f"  响应前 400 字: {txt[:400]}")
        out[name] = {"status": r.status_code, "head": txt[:400]}
        return r.status_code, txt
    except Exception as exc:
        print(f"  [!] 异常 {type(exc).__name__}: {exc}")
        out[name] = {"status": None, "error": str(exc)[:200]}
        return None, ""


# 1. Key 有效性
probe(
    "1 Coding Plan Key 有效性",
    "POST",
    "/chat/completions",
    {"model": "qwen3.8-flash", "messages": [{"role": "user", "content": "回复：可用"}], "max_tokens": 10},
)

# 2. 全部模型
st, txt = probe("2 全部模型列表", "GET", "/models")
model_ids = []
if st == 200:
    try:
        data = json.loads(txt).get("data", [])
        model_ids = sorted({m.get("id", "") for m in data})
        print(f"\n  共 {len(model_ids)} 个模型：")
        for i in model_ids:
            print(f"    {i}")
    except Exception as exc:
        print(f"  [!] 解析模型列表失败: {exc}")

# 3. 找 rerank / embedding 候选
cand = [i for i in model_ids if ("rerank" in i.lower() or "rank" in i.lower() or "embed" in i.lower())]
print(f"\n[3] rerank/embedding 候选: {cand}")

# 4. 逐个实测 /rerank
print("\n[4] 逐个实测 /rerank：")
for m in cand or ["qwen3-rerank", "text-rerank-v1", "gte-rerank"]:
    probe(
        f"rerank::{m}",
        "POST",
        "/rerank",
        {"model": m, "query": QUERY, "documents": DOCS, "top_n": 3},
    )

# 5. embedding 候选实测
emb = [i for i in model_ids if "embed" in i.lower()]
if emb:
    print("\n[5] 实测 /embeddings：")
    probe(f"embeddings::{emb[0]}", "POST", "/embeddings", {"model": emb[0], "input": "测试文本"})

print("")
print("=" * 66)
print("结论")
print("=" * 66)
for k, v in out.items():
    print(f"  {k}: HTTP {v.get('status')}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_codingplan_rerank_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump({"models": model_ids, "probes": out}, f, ensure_ascii=False, indent=2)
