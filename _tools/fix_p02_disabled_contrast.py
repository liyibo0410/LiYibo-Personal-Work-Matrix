"""修 P02 里「禁用态白字配浅灰底」的回归。

背景：globals.css 的 fill-3 原本为深色主题取 #222836（深灰），
改成白底后我把它换成 #E4E9F1（浅灰）。但组件里普遍写着
`text-white ... disabled:bg-fill-3` —— 按钮一禁用就成了白字配浅灰底，文字直接看不见。
禁用态必须同时把文字压成中性灰，而不是只换底色。

顺带修 settings 的状态圆点：`bg-fill-3` 在白底上几乎不可见，换 ink-4。
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "projects/p02-ecommerce-ops-assistant/web/src"
BACKUP = ROOT / "_runtime/p02-disabled-backup"

# (相对 src 的文件, 旧片段, 新片段, 期望命中)
EDITS = [
    ("app/(app)/agent/page.tsx",
     "disabled:cursor-not-allowed disabled:bg-fill-3",
     "disabled:cursor-not-allowed disabled:bg-fill-3 disabled:text-ink-3", 1),
    ("app/(app)/agent/page.tsx",
     'font-medium text-white disabled:bg-fill-3"',
     'font-medium text-white disabled:bg-fill-3 disabled:text-ink-3"', 1),
    ("components/agent-run-panel.tsx",
     "disabled:cursor-not-allowed disabled:bg-fill-3",
     "disabled:cursor-not-allowed disabled:bg-fill-3 disabled:text-ink-3", 1),
    ("components/inventory-advice-panel.tsx",
     "disabled:cursor-not-allowed disabled:bg-fill-3",
     "disabled:cursor-not-allowed disabled:bg-fill-3 disabled:text-ink-3", 1),
    ("components/product-import-panel.tsx",
     "disabled:cursor-not-allowed disabled:bg-fill-3",
     "disabled:cursor-not-allowed disabled:bg-fill-3 disabled:text-ink-3", 1),
    ("app/(app)/settings/page.tsx",
     '${active ? "bg-success" : "bg-fill-3"}',
     '${active ? "bg-success" : "bg-ink-4"}', 1),
]


def main() -> int:
    problems: list[str] = []
    touched: set[pathlib.Path] = set()
    for rel, old, new, want in EDITS:
        path = SRC / rel
        if not path.is_file():
            problems.append(f"{rel} 不存在")
            continue
        text = path.read_text(encoding="utf-8")
        got = text.count(old)
        if got != want:
            problems.append(f"{rel}：「{old[:44]}」命中 {got} 次，期望 {want} 次")
            continue
        dst = BACKUP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(path, dst)
        path.write_text(text.replace(old, new), encoding="utf-8", newline="")
        touched.add(rel)
    sys.stdout.write(f"改过 {len(touched)} 个文件：{sorted(touched)}\n")
    for p in problems:
        sys.stdout.write("  ! " + p + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
