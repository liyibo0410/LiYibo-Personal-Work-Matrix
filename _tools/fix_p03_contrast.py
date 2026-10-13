"""修 P03 前端在白底下的对比度缺陷（深色时代遗留写法）。

三类问题：
1. 用「边框色」当文字色 —— 深底上是暗灰幽灵字，白底上直接看不见（用户反馈的「经营问数看不见了」）。
2. hover 用 rgba(255,255,255,.1) 白色叠加 —— 白底上等于没有反馈。
3. 渐变里混进第二个蓝 #5B8DEF —— 与品牌蓝不同色相，用户反馈的「还有青色蓝色」。
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "projects/p03-deep-research/ui/src/App.vue"
BACKUP = ROOT / "_runtime/whiteblue-backup/p03-contrast/App.vue"

PAIRS = [
    ("  color: var(--border-color);", "  color: var(--text-secondary);", 4),
    ("  background: rgba(255, 255, 255, 0.1);", "  background: var(--cp-elevated);", 3),
    ('<stop offset="1" stop-color="#5B8DEF"/>', '<stop offset="1" stop-color="#245AE0"/>', 1),
    ("background: linear-gradient(90deg, var(--accent), #5B8DEF);",
     "background: linear-gradient(90deg, var(--accent), var(--accent-hover));", 1),
    ("  color: #ff6b6b;", "  color: var(--cp-danger);", 1),
    ("  background: #3A4560;", "  background: var(--cp-elevated);", 1),
]


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    problems = []
    for old, new, want in PAIRS:
        got = text.count(old)
        if got != want:
            problems.append(f"「{old.strip()[:52]}」命中 {got} 次，期望 {want} 次 —— 跳过")
            continue
        text = text.replace(old, new)
    if not problems:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        if not BACKUP.exists():
            shutil.copy2(TARGET, BACKUP)
        TARGET.write_text(text, encoding="utf-8", newline="")
    sys.stdout.write("P03 对比度修复完成\n" if not problems else "有未命中的模式：\n")
    for p in problems:
        sys.stdout.write("  - " + p + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
