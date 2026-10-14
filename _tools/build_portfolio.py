# -*- coding: utf-8 -*-
"""把 01-portfolio/index.html 打成自包含的发布产物 dist/index.html。

源文件按 ADR-0005 用 `@import url('../shared/ui-kit/*.css')` 引设计令牌；
但站点是独立发布的，`../shared/` 在公网不存在 —— 上一版发布后访客打开就是无样式裸页
（实测 https://...qoder.zone/shared/ui-kit/tokens.css → 404）。所以发布前把令牌与组件
样式内联进去，保持「单一真源」又让产物自足。

    python _tools/build_portfolio.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "01-portfolio" / "index.html"
OUT = REPO / "01-portfolio" / "dist" / "index.html"
IMPORT_RE = re.compile(r"@import\s+url\(['\"]([^'\"]+)['\"]\);?")


def inline(css: str, base: Path, depth: int = 0) -> str:
    """递归展开 @import，把相对路径的 CSS 换成文件内容。"""
    if depth > 4:
        raise RuntimeError("@import 嵌套过深，可能有循环引用")

    def repl(m: re.Match) -> str:
        ref = m.group(1)
        if ref.startswith(("http://", "https://")):
            return m.group(0)                      # 外链保留原样，交给浏览器
        path = (base / ref).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"@import 指向不存在的文件：{path}")
        return "/* ── inlined %s ── */\n%s\n" % (
            path.name, inline(path.read_text(encoding="utf-8"), path.parent, depth + 1))

    return IMPORT_RE.sub(repl, css)


def main() -> int:
    html = SRC.read_text(encoding="utf-8")
    built = inline(html, SRC.parent)
    left = IMPORT_RE.findall(built)
    if left:
        print("[失败] 仍有未内联的 @import：%s" % ", ".join(left))
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(built, encoding="utf-8")
    print("已生成 %s" % OUT.relative_to(REPO))
    print("  源 %s → 产物 %.1f KB（令牌与组件样式已内联，可独立发布）"
          % (SRC.name, len(built.encode("utf-8")) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
