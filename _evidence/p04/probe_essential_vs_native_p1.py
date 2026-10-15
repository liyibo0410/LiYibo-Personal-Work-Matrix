# _evidence/p04/probe_essential_vs_native_p1.py
# 铁证对照：同一个 DashScope 原生 rerank 端点，sk-sp-(Essential/Token Plan) vs sk-ws-(Coding Plan)
# 目的：证明"不能用 Essential"是套餐能力边界，不是模型名或端点写错
# 安全：Key 从 .env 读 / 环境变量传，日志不落盘明文

from __future__ import annotations

import os
import sys
import json
import io
from pathlib import Path

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p04-rag-knowledge-base"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
ESSENTIAL = os.getenv("MCP_API_KEY", "")          # sk-sp-  (Essential / Token Plan)
CODING = os.environ.get("WS_API_KEY", "")          # sk-ws-  (Coding Plan)

print(f"[info] Essential(sk-sp-): prefix={ESSENTIAL[:7]!r} len={len(ESSENTIAL)}")
print(f"[info] Coding   (sk-ws-): prefix={CODING[:7]!r} len={len(CODING)}")
print("       (Key 明文不打印)")

import httpx

NATIVE = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行，请各部门报名。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
]

# 用已经验证正确的模型名，排除"模型名写错"这个变量
MODEL = "qwen3.7-text-rerank"

out = {}


def run(tag, key):
    if not key:
        print(f"\n  {tag}: 无 Key，跳过")
        out[tag] = {"status": None, "note": "no key"}
        return
    H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "input": {"query": QUERY, "documents": DOCS},
        "parameters": {"top_n": 3, "return_documents": False},
    }
    print("\n" + "=" * 68)
    print(f"  {tag}")
    print(f"  POST {NATIVE}   model={MODEL}")
    print("=" * 68)
    got = None
    for use_proxy in (False, True):  # 先关代理，排除沙箱代理干扰
        try:
            with httpx.Client(timeout=45, trust_env=use_proxy) as c:
                r = c.post(NATIVE, headers=H, json=body)
            print(f"  代理={'开' if use_proxy else '关'} -> HTTP {r.status_code}")
            print(f"    响应: {r.text[:260]}")
            if got is None:
                got = {"status": r.status_code, "head": r.text[:260]}
        except Exception as exc:
            print(f"  代理={'开' if use_proxy else '关'} -> 异常 {type(exc).__name__}: {str(exc)[:120]}")
    out[tag] = got or {"status": None}


run("A. Essential(sk-sp-) 打原生 rerank", ESSENTIAL)
run("B. Coding(sk-ws-)   打原生 rerank（对照组，已知成功）", CODING)

print("\n" + "=" * 68)
print("结论对照")
print("=" * 68)
for k, v in out.items():
    print(f"  {k}: HTTP {v.get('status')}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_essential_vs_native_p1.json"),
    "w",
    encoding="utf-8",
) as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
