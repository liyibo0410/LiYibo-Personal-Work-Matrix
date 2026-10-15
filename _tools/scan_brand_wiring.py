# -*- coding: utf-8 -*-
"""扫描各模块前端页面的品牌绑定情况：data-cp-brand 节点 / loadBrand 调用 / 硬编码公司名。"""
import os
import re
import json

SKIP_DIRS = {"node_modules", ".next", "dist", ".venv", "site-packages",
             "_evidence", ".git", "__pycache__", "external", "_tmp_issue",
             "_site_8120", "learning-guide", "eval_report", "output"}
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

rows = []
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for name in files:
        if not name.endswith((".html", ".tsx", ".jsx")):
            continue
        p = os.path.join(root, name)
        try:
            text = open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        binds = re.findall(r'data-cp-brand(?:-title)?="([^"]+)"', text)
        calls = len(re.findall(r'CP\.loadBrand|loadBrand\(|applyBrand\(|cp:brand', text))
        hard = len(re.findall(r'李奕波个人作品矩阵|Li Yibo's Personal Portfolio', text))
        if not (binds or hard or calls):
            continue
        rows.append({
            "file": os.path.relpath(p, REPO).replace("\\", "/"),
            "binds": sorted(set(binds)),
            "bridge_calls": calls,
            "hardcoded_name_hits": hard,
        })

rows.sort(key=lambda r: r["file"])
print(json.dumps(rows, ensure_ascii=False, indent=1))
