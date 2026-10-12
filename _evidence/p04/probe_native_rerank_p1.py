# _evidence/p04/probe_native_rerank_p1.py
# 用 sk-ws- (Coding Plan) Key 测 DashScope 原生 rerank 端点
# 区分：是"代理不通(502)"还是"Key/权限不对(401/403)"
# 安全：Key 由环境变量传入，日志不落盘 Key 明文

from __future__ import annotations

import os
import sys
import json
import io

KEY = os.environ.get("WS_API_KEY", "")
print(f"[info] Key prefix={KEY[:7]!r} len={len(KEY)}  (不打印明文)")
if not KEY:
    sys.exit(1)

import httpx

QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行，请各部门报名。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
]

H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

TARGETS = [
    (
        "A 原生 rerank（官方标准端点）",
        "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
        {
            "model": "qwen3.7-text-rerank",
            "input": {"query": QUERY, "documents": DOCS},
            "parameters": {"top_n": 3, "return_documents": False},
        },
    ),
    (
        "B 兼容端点 /rerank（已确认 404，复现）",
        "https://ws-amdqcpdtt4gdo5ax.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/rerank",
        {"model": "qwen3.7-text-rerank", "query": QUERY, "documents": DOCS, "top_n": 3},
    ),
]

out = {}
for name, url, body in TARGETS:
    for use_proxy in (True, False):
        tag = f"{name} | 代理={'开' if use_proxy else '关'}"
        print("")
        print("=" * 70)
        print(f"  {tag}")
        print(f"  POST {url}")
        print("=" * 70)
        try:
            with httpx.Client(timeout=45, trust_env=use_proxy) as c:
                r = c.post(url, headers=H, json=body)
            txt = r.text[:500]
            print(f"  HTTP {r.status_code}")
            print(f"  响应: {txt}")
            out[tag] = {"status": r.status_code, "head": txt}
        except Exception as exc:
            msg = f"{type(exc).__name__}: {str(exc)[:200]}"
            print(f"  [!] {msg}")
            out[tag] = {"status": None, "error": msg}

print("")
print("=" * 70)
print("结论")
print("=" * 70)
for k, v in out.items():
    print(f"  {k}: HTTP {v.get('status')}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_native_rerank_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
