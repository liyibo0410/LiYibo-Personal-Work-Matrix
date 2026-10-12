#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检测 web/src 中的 UTF-8 被当作 GBK 解码产生的乱码（mojibake）。

原理：乱码串是「原始 UTF-8 字节 → 以 GBK 解码」的产物。
反向操作：乱码串 .encode('gbk').decode('utf-8') 若成功且仍含中文，即为乱码，并可得到原文。
合法中文编码为 GBK 后通常不是合法 UTF-8，因此该反演几乎只命中乱码。
输出 JSON 清单，供人工/脚本修复；--check 模式：有命中则退出码 1（用于 CI 防回归）。
"""
import io
import json
import os
import re
import sys

ROOT = r"D:/software/PycharmProjects/ecommerce-operation-assistant/web/src"
OUT = r"D:/software/PycharmProjects/ecommerce-operation-assistant/scripts/mojibake-report.json"
RUN = re.compile(r"[^\x00-\x7f]+")


def reverse(run: str):
    try:
        raw = run.encode("gbk")
    except UnicodeEncodeError:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if text != run and re.search(r"[\u4e00-\u9fff]", text):
        return text
    return None


def main():
    hits = []
    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith((".ts", ".tsx")):
                continue
            path = os.path.join(dirpath, fn)
            with io.open(path, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    for m in RUN.finditer(line):
                        fixed = reverse(m.group(0))
                        if fixed:
                            hits.append({
                                "file": os.path.relpath(path, ROOT).replace("\\", "/"),
                                "line": lineno,
                                "orig": m.group(0),
                                "fixed": fixed,
                            })
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    print(f"[check-mojibake] 命中 {len(hits)} 处乱码；清单见 {OUT}")
    if "--check" in sys.argv and hits:
        sys.exit(1)


if __name__ == "__main__":
    main()
