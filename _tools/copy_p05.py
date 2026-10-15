# -*- coding: utf-8 -*-
"""D4 第一步：把「衡鉴 v2.0」复制进作品集 projects/p05-contract-review

排除项：
  - __pycache__ / *.pyc / *.pyo   构建缓存
  - data/review.db*               运行时数据库（首次启动自动重建）
  - data/mock_approval.json       模拟审批种子数据（启动时按 force_reseed 重建）
  - data/access.log               访问日志
  - *.bak                         Qoder/P1 修改前的备份文件

复制完成后写一份 manifest 供核对。
"""
from __future__ import annotations

import io
import json
import os
import shutil

SRC = r"D:\software\PycharmProjects\合同审批系统-李奕波\05-可运行系统-contract-review-v2.0"
DST = r"D:\software\PycharmProjects\作品矩阵\projects\p05-contract-review"
REPORT = r"D:\software\PycharmProjects\作品矩阵\_evidence\p05\copy_report.json"

IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".idea", ".venv", "venv"}
IGNORE_SUFFIX = (".pyc", ".pyo", ".bak")
IGNORE_REL = {
    "data/review.db",
    "data/review.db-shm",
    "data/review.db-wal",
    "data/mock_approval.json",
    "data/access.log",
}


def make_ignore(src_root):
    def _ignore(dirpath, names):
        rel = os.path.relpath(dirpath, src_root).replace("\\", "/")
        rel = "" if rel == "." else rel
        drop = []
        for n in names:
            if n in IGNORE_DIRS:
                drop.append(n)
                continue
            if n.endswith(IGNORE_SUFFIX):
                drop.append(n)
                continue
            r = (rel + "/" + n) if rel else n
            if r in IGNORE_REL:
                drop.append(n)
        return set(drop)

    return _ignore


def main():
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    os.makedirs(DST, exist_ok=True)

    if not os.path.isdir(SRC):
        raise SystemExit("SRC not found: %s" % SRC)

    shutil.copytree(SRC, DST, ignore=make_ignore(SRC), dirs_exist_ok=True)

    # 清点
    n_files = 0
    n_dirs = 0
    total = 0
    top = []
    for dirpath, dirnames, filenames in os.walk(DST):
        n_dirs += len(dirnames)
        for f in filenames:
            n_files += 1
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
        if os.path.normpath(dirpath) == os.path.normpath(DST):
            top = sorted(dirnames) + sorted(filenames)

    rep = {
        "src": SRC,
        "dst": DST,
        "files": n_files,
        "dirs": n_dirs,
        "bytes": total,
        "mb": round(total / 1024 / 1024, 2),
        "top_level": top,
    }
    with io.open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print("copied files=%d dirs=%d size=%.2fMB" % (n_files, n_dirs, rep["mb"]))


if __name__ == "__main__":
    main()
