# _tools/fix_env_rerank_p1.py
# P1 执行返工单第 ⑥ 项：修正 .env 的 cloud 重排配置
#   MCP_API_KEY        : sk-sp-(Essential，无 rerank 权限) -> sk-ws-(Coding Plan)
#   TEXT_RERANK_MODEL  : qwen3-rerank(模型名不存在)        -> qwen3.7-text-rerank
# 安全：新 Key 由环境变量 WS_API_KEY 传入，脚本文件本身不含 Key 明文；日志不打印 Key

from __future__ import annotations

import io
import os
import shutil
import sys

ROOT = r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base"
ENV_PATH = os.path.join(ROOT, ".env")
BAK_PATH = os.path.join(ROOT, ".env.p1bak")

NEW_KEY = os.environ.get("WS_API_KEY", "").strip()
if not NEW_KEY:
    print("[!] 未读到环境变量 WS_API_KEY，退出")
    sys.exit(1)
print(f"[info] 待写入 Key: prefix={NEW_KEY[:7]!r} len={len(NEW_KEY)}  (不打印明文)")

if not os.path.exists(ENV_PATH):
    print(f"[!] 未找到 {ENV_PATH}")
    sys.exit(1)

# 1) 备份
if not os.path.exists(BAK_PATH):
    shutil.copy2(ENV_PATH, BAK_PATH)
    print(f"[backup] -> {BAK_PATH}")
else:
    print(f"[backup] 已存在，跳过: {BAK_PATH}")

# 2) 逐行改写（保留注释、顺序、其它键不变）
TARGETS = {
    "MCP_API_KEY": NEW_KEY,
    "TEXT_RERANK_MODEL": "qwen3.7-text-rerank",
}

with io.open(ENV_PATH, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

changed: dict[str, tuple[str, str]] = {}
out_lines = []
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        k, _, v = stripped.partition("=")
        k = k.strip()
        if k in TARGETS:
            old = v.strip()
            new = TARGETS[k]
            if old != new:
                changed[k] = (old if k != "MCP_API_KEY" else f"{old[:7]}...(len={len(old)})",
                              new if k != "MCP_API_KEY" else f"{new[:7]}...(len={len(new)})")
            out_lines.append(f"{k} = {new}")
            continue
    out_lines.append(line)

with io.open(ENV_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out_lines) + "\n")

print("\n[changed]")
for k, (o, n) in changed.items():
    print(f"  {k}: {o}  ->  {n}")
if not changed:
    print("  (无变化)")

# 3) 回读校验（不打印 Key 明文）
print("\n[verify] 回读：")
with io.open(ENV_PATH, "r", encoding="utf-8") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            k, v = k.strip(), v.strip()
            if k in TARGETS:
                if k == "MCP_API_KEY":
                    print(f"  {k} = {v[:7]}...(len={len(v)})")
                else:
                    print(f"  {k} = {v}")

print("\n[done]")
