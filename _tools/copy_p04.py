# -*- coding: utf-8 -*-
"""D5 第一步：把「BOSS 智库」（RAG 知识库）复制进作品集 projects/p04-rag-knowledge-base

排除项（比 P05 更严格，因为本项目体积集中在环境与容器数据）：
  - .venv/           4.9 GB（虚拟环境，凭 pyproject.toml 重建，不入库）
  - volumes/         487 MB（Milvus/etcd/MinIO/Mongo 容器数据，运行时产物）
  - .git/            源项目版本历史（作品集用自己的仓库）
  - .env             ★ 含真实 API Key，绝不能进作品集（只复制 .env.example）
  - __pycache__ / *.pyc / *.log / .idea
"""
from __future__ import annotations

import io
import json
import os
import shutil

SRC = r"D:\software\PycharmProjects\knowledge_base"
DST = r"D:\software\PycharmProjects\面试项目\projects\p04-rag-knowledge-base"
REPORT = r"D:\software\PycharmProjects\面试项目\_evidence\p04\copy_report.json"

IGNORE_DIRS = {"__pycache__", ".venv", "venv", ".git", ".idea", "volumes",
               ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
IGNORE_SUFFIX = (".pyc", ".pyo", ".bak", ".log", ".tmp")
IGNORE_NAMES = {".env", "svc_pid.txt", "1.3.3"}


def make_ignore(src_root):
    def _ignore(dirpath, names):
        drop = set()
        for n in names:
            if n in IGNORE_DIRS:
                drop.add(n)
                continue
            if n in IGNORE_NAMES:
                drop.add(n)
                continue
            if n.endswith(IGNORE_SUFFIX):
                drop.add(n)
        return drop

    return _ignore


def main():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    os.makedirs(DST, exist_ok=True)

    if not os.path.isdir(SRC):
        raise SystemExit("SRC not found: %s" % SRC)

    shutil.copytree(SRC, DST, ignore=make_ignore(SRC), dirs_exist_ok=True)

    n_files = 0
    n_dirs = 0
    total = 0
    top = []
    for dirpath, dirnames, filenames in os.walk(DST):
        n_dirs += len(dirnames)
        for f in filenames:
            n_files += 1
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
        if os.path.normpath(dirpath) == os.path.normpath(DST):
            top = sorted(dirnames) + sorted(filenames)

    # 安全断言：绝不能带 .env 进来
    leaked = [f for f in top if f == ".env"]
    rep = {
        "src": SRC, "dst": DST,
        "files": n_files, "dirs": n_dirs,
        "bytes": total, "mb": round(total / 1024 / 1024, 2),
        "top_level": top,
        "env_leaked": leaked,
    }
    with io.open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print("copied files=%d dirs=%d size=%.2fMB env_leaked=%s" %
          (n_files, n_dirs, rep["mb"], leaked or "none"))
    return 0 if not leaked else 1


if __name__ == "__main__":
    raise SystemExit(main())
