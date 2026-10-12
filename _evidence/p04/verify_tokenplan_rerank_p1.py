# _evidence/p04/verify_tokenplan_rerank_p1.py
# P1 实测：sk-sp- (Token Plan) Key 到底能不能跑云端 rerank
# 安全：Key 从 .env 读取，脚本与日志均不落盘 Key 明文

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

load_dotenv(os.path.join(ROOT, ".env"))  # 显式指定，否则会从脚本所在目录往上找

KEY = os.getenv("MCP_API_KEY", "")
print(f"[info] 读到 MCP_API_KEY: prefix={KEY[:7]!r} len={len(KEY)}  (Key 本身不打印)")

import httpx

TP_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
DS_NATIVE = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行。",
    "住宿费报销须开具增值税专用发票。",
]

results = {}


def probe(name, method, url, *, headers=None, json_body=None, timeout=40):
    print("")
    print("=" * 66)
    print(f"  {name}")
    print(f"  {method} {url}")
    print("=" * 66)
    try:
        with httpx.Client(timeout=timeout) as c:
            if method == "GET":
                r = c.get(url, headers=headers)
            else:
                r = c.post(url, headers=headers, json=json_body)
        body = r.text
        print(f"  HTTP {r.status_code}")
        print(f"  响应前 300 字: {body[:300]}")
        results[name] = {"status": r.status_code, "body_head": body[:300]}
        return r.status_code, body
    except Exception as exc:
        print(f"  [!] 请求异常: {type(exc).__name__}: {exc}")
        results[name] = {"status": None, "error": str(exc)[:200]}
        return None, str(exc)


H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ── 1. 确认 Key 本身有效（chat/completions）──
probe(
    "1 Token Plan Key 有效性（chat/completions）",
    "POST",
    f"{TP_BASE}/chat/completions",
    headers=H,
    json_body={
        "model": "qwen3.7-plus",
        "messages": [{"role": "user", "content": "回复两个字：可用"}],
        "max_tokens": 10,
    },
)

# ── 2. 看 Token Plan 端点上有哪些模型（有没有 rerank）──
probe("2 Token Plan 可用模型列表", "GET", f"{TP_BASE}/models", headers=H)

# ── 3. 试兼容端点的 /rerank（OpenAI 兼容风格）──
probe(
    "3 兼容端点 /rerank",
    "POST",
    f"{TP_BASE}/rerank",
    headers=H,
    json_body={"model": "qwen3-rerank", "query": QUERY, "documents": DOCS, "top_n": 3},
)

# ── 4. 试 dashscope 原生 rerank（复现当前 401）──
probe(
    "4 DashScope 原生 rerank（当前代码的调用路径）",
    "POST",
    DS_NATIVE,
    headers=H,
    json_body={
        "model": "qwen3-rerank",
        "input": {"query": QUERY, "documents": DOCS},
        "parameters": {"top_n": 3, "return_documents": False},
    },
)

print("")
print("=" * 66)
print("结论")
print("=" * 66)
for k, v in results.items():
    print(f"  {k}: HTTP {v.get('status')}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_tokenplan_rerank_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
