"""P02：把 `bg-ink-1` 当按钮/面板底色用的 51 处统一到品牌蓝，并修掉「深色块」。

为什么非改不可：`--color-ink-1` 是**文字色**令牌（ink = 墨）。深色主题下它 = #E8EAF0（近白），
所以 `bg-ink-1 text-white` 一直是「白字配近白底」——按钮和面板文字本来就看不清；
改成白底主题后它 = #1A1F2B（深藏青），文字能读了，但在一片白页面上留下 51 块深色，
就是用户说的「颜色不统一、还有深色块」。

做法：
1. 先单独处理两处真正当**面板/代码块**用的（不是按钮），改成浅色面 + 深色字。
2. 其余按按钮处理：hover 变深、底色换品牌蓝。
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "projects/p02-ecommerce-ops-assistant/web/src"
BACKUP = ROOT / "_runtime/p02-blue-backup"

# 先做定向替换（用改前的原文匹配）
SPECIFIC: list[tuple[str, str, str, int]] = [
    # Agent 页的「Harness 边界」面板：整块深底 → 品牌蓝弱底 + 深色字
    ("app/(app)/agent/page.tsx",
     '<div className="rounded-lg border border-line bg-ink-1 p-5 text-white">',
     '<div className="rounded-lg border border-brand-200 bg-brand-50 p-5 text-ink-1">', 1),
    ("app/(app)/agent/page.tsx",
     '<div key={title} className="rounded-lg border border-border-ink-4 bg-ink-1 p-3">',
     '<div key={title} className="rounded-lg border border-line bg-surface p-3">', 1),
    ("app/(app)/agent/page.tsx",
     '<p className="font-medium text-white">{title}</p>',
     '<p className="font-medium text-ink-1">{title}</p>', 1),
    ("app/(app)/agent/page.tsx",
     '<div className="mt-5 grid gap-3 text-sm text-ink-3 sm:grid-cols-2">',
     '<div className="mt-5 grid gap-3 text-sm text-ink-2 sm:grid-cols-2">', 1),
    # 生成任务详情里的 JSON 代码块：深底 → 浅灰底 + 正文色
    ("app/(app)/products/[id]/generation-jobs/[jobId]/page.tsx",
     'rounded-lg bg-ink-1 p-3 text-xs leading-5 text-text-ink-4',
     'rounded-lg bg-fill-2 p-3 text-xs leading-5 text-ink-2', 1),
]

# 再做全局按钮替换：hover 必须先换，否则会被下一条吞掉
GLOBAL: list[tuple[str, str]] = [
    ("hover:bg-ink-1", "hover:bg-brand-700"),
    ("bg-ink-1", "bg-brand-600"),
]


def main() -> int:
    problems: list[str] = []

    files: dict[pathlib.Path, str] = {}
    for p in SRC.rglob("*.tsx"):
        files[p] = p.read_text(encoding="utf-8")

    for rel, old, new, want in SPECIFIC:
        path = SRC / rel
        text = files[path]
        got = text.count(old)
        if got != want:
            problems.append(f"{rel}：定向片段命中 {got} 次，期望 {want} —— 跳过")
            continue
        files[path] = text.replace(old, new)

    hits = 0
    for path, text in files.items():
        new_text = text
        for old, repl in GLOBAL:
            hits += new_text.count(old)
            new_text = new_text.replace(old, repl)
        if new_text != text:
            rel = path.relative_to(SRC).as_posix()
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(path, dst)
            path.write_text(new_text, encoding="utf-8", newline="")

    sys.stdout.write(f"替换 {hits} 处底色；定向修 5 处面板/代码块\n")
    for p in problems:
        sys.stdout.write("  ! " + p + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
