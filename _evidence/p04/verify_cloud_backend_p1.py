# _evidence/p04/verify_cloud_backend_p1.py
# P1 验证返工单第 ⑥ 项：改完 .env 后，cloud 重排是否真的走通（不是只改配置就算完）
# 验证三层：① 配置读对 ② rerank_documents() 真走 cloud ③ 分数落在 0~1 量纲
# 附带：确认 .env 与 .env.p1bak 均被 gitignore（安全红线）

from __future__ import annotations

import os
import sys
import json
import io
import subprocess

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p04-rag-knowledge-base"
REPO = r"D:\software\PycharmProjects\作品矩阵"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# 必须在 import 配置模块之前设定后端
os.environ["RERANK_BACKEND"] = "cloud"

from config.reranker_config import reranker_config as rc
from utils.reranker_http_utils import (
    rerank_documents,
    get_last_rerank_status,
    reset_local_reranker,
)

OUT = {}


def log(m):
    print(m, flush=True)


log("=" * 68)
log("P1 验证 · 第 ⑥ 项 .env 配置修正后 cloud 重排是否真通")
log("=" * 68)

# ① 配置读对
log(f"\n[1] 配置读取")
log(f"    backend            = {rc.backend}")
log(f"    text_rerank_model  = {rc.text_rerank_model}")
log(f"    api_key            = {rc.text_rerank_api_key[:7]}...(len={len(rc.text_rerank_api_key or '')})")
OUT["config"] = {
    "backend": rc.backend,
    "model": rc.text_rerank_model,
    "key_prefix": rc.text_rerank_api_key[:7] if rc.text_rerank_api_key else None,
}

ok_model = rc.text_rerank_model == "qwen3.7-text-rerank"
ok_key = bool(rc.text_rerank_api_key) and rc.text_rerank_api_key.startswith("sk-ws-")
log(f"    模型名正确: {ok_model}   Key 为 sk-ws-: {ok_key}")

# ② 真跑 cloud
QUERY = "员工报销差旅费需要提交哪些凭证"
DOCS = [
    "差旅费报销需提供机票行程单和酒店发票。",
    "公司年会将于下周五举行，请各部门报名。",
    "住宿费报销须开具增值税专用发票，抬头与税号一致。",
]

reset_local_reranker()
log(f"\n[2] 调用 rerank_documents(backend=cloud)")
try:
    scores = rerank_documents(QUERY, DOCS)
    st = get_last_rerank_status()
    log(f"    backend        = {st['backend']}")
    log(f"    degrade_reason = '{st['degrade_reason']}'")
    log(f"    scores         = {[round(s, 4) for s in scores]}")
    OUT["cloud"] = {
        "backend": st["backend"],
        "degrade": st["degrade_reason"],
        "scores": [round(s, 4) for s in scores],
    }

    ok_cloud = st["backend"] == "cloud"
    ok_range = bool(scores) and all(0.0 <= s <= 1.0 for s in scores)
    ok_order = bool(scores) and scores[0] > scores[-1]
    log(f"\n    真走 cloud: {ok_cloud}")
    log(f"    分数落在 0~1: {ok_range}   （云端 relevance_score 量纲）")
    log(f"    排序符合语义: {ok_order}   （最相关 {scores[0]:.4f} > 最不相关 {scores[-1]:.4f}）")
    OUT["cloud_ok"] = ok_cloud and ok_range and ok_order
except Exception as exc:
    log(f"    [!] 调用失败: {type(exc).__name__}: {exc}")
    OUT["cloud_ok"] = False
    OUT["cloud_error"] = str(exc)[:300]

# ③ local 不回归（切回 local 再跑一次）
log(f"\n[3] 回归检查：切回 local")
from config import reranker_config as rc_mod

rc_mod.reranker_config.backend = "local"
reset_local_reranker()
try:
    s2 = rerank_documents(QUERY, DOCS)
    st2 = get_last_rerank_status()
    log(f"    backend = {st2['backend']}   scores = {[round(s, 4) for s in s2]}")
    OUT["local_ok"] = st2["backend"] == "local"
except Exception as exc:
    log(f"    [!] local 失败: {exc}")
    OUT["local_ok"] = False

# ④ 安全红线：.env 与 .env.p1bak 是否被 gitignore
log(f"\n[4] 安全红线：敏感文件是否被 gitignore")
for rel in ("projects/p04-rag-knowledge-base/.env",
            "projects/p04-rag-knowledge-base/.env.p1bak"):
    try:
        r = subprocess.run(
            ["git", "check-ignore", "-v", rel],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        ignored = r.returncode == 0
        log(f"    {rel:<52} ignored={ignored}")
        if ignored:
            log(f"        规则: {r.stdout.strip()}")
        OUT.setdefault("gitignore", {})[rel] = ignored
    except Exception as exc:
        log(f"    {rel}: 检查失败 {exc}")
        OUT.setdefault("gitignore", {})[rel] = None

log("\n" + "=" * 68)
log("汇总")
log("=" * 68)
log(f"  配置正确      : {ok_model and ok_key}")
log(f"  cloud 真通    : {OUT.get('cloud_ok')}")
log(f"  local 无回归  : {OUT.get('local_ok')}")
log(f"  敏感文件已忽略: {OUT.get('gitignore')}")

with io.open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_cloud_backend_p1.json"),
    "w", encoding="utf-8",
) as f:
    json.dump(OUT, f, ensure_ascii=False, indent=2)
