#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书设计令牌迁移脚本（P0 一致性债收敛）。

把 web/src 下仍使用旧 Tailwind 调色板（slate/cyan/emerald/gray/zinc/neutral/blue/
red/amber/green + 硬编码 hex）的 className 批量替换为 globals.css 中定义的飞书令牌，
并把 rounded-md 统一成 rounded-lg。支持 --check 模式（只扫描不写文件，用于 CI 防回归）。

映射原则：
- 文字色 slate-300/400 -> ink-3, slate-500 -> ink-2, slate-600+ -> ink-1
- 填充底 slate-50 -> fill-1, slate-100/200 -> fill-2, slate-300/400 -> fill-3, 深色面 -> ink-1/ink-2
- 线/边框 slate-200 -> line
- 品牌色 cyan-700 -> brand-600, cyan-600 -> brand-500（飞书蓝）
- 成功色 emerald -> success（浅底 emerald-50 -> success-bg）
- 危险/警告 red/amber -> danger/warning（浅底 -> *-bg）
- 变体（hover:/focus:/md: ...）原样保留，只替换颜色部分
- 任意值 hex（bg-[#...]）不自动替换，单独列出待人工处理
"""
import os
import re
import sys

ROOT = r"D:/software/PycharmProjects/ecommerce-operation-assistant/web/src"
VARIANT = r"(?:(?:hover|focus|focus-within|active|disabled|dark|sm|md|lg|xl|2xl|group-hover|group-focus):)*"

# (prefix, oldcolor) -> newcolor
MAP = {
    # ---- text ----
    ("text-", "slate-300"): "ink-3", ("text-", "slate-400"): "ink-3", ("text-", "slate-500"): "ink-2",
    ("text-", "slate-600"): "ink-1", ("text-", "slate-700"): "ink-1", ("text-", "slate-800"): "ink-1", ("text-", "slate-900"): "ink-1",
    ("text-", "gray-300"): "ink-3", ("text-", "gray-400"): "ink-3", ("text-", "gray-500"): "ink-2",
    ("text-", "gray-600"): "ink-1", ("text-", "gray-700"): "ink-1", ("text-", "gray-800"): "ink-1", ("text-", "gray-900"): "ink-1",
    ("text-", "zinc-300"): "ink-3", ("text-", "zinc-400"): "ink-3", ("text-", "zinc-500"): "ink-2",
    ("text-", "zinc-600"): "ink-1", ("text-", "zinc-700"): "ink-1", ("text-", "zinc-800"): "ink-1", ("text-", "zinc-900"): "ink-1",
    ("text-", "neutral-300"): "ink-3", ("text-", "neutral-400"): "ink-3", ("text-", "neutral-500"): "ink-2",
    ("text-", "neutral-600"): "ink-1", ("text-", "neutral-700"): "ink-1", ("text-", "neutral-800"): "ink-1", ("text-", "neutral-900"): "ink-1",
    ("text-", "cyan-400"): "brand-500", ("text-", "cyan-500"): "brand-500", ("text-", "cyan-600"): "brand-600", ("text-", "cyan-700"): "brand-600",
    ("text-", "blue-400"): "brand-500", ("text-", "blue-500"): "brand-500", ("text-", "blue-600"): "brand-600", ("text-", "blue-700"): "brand-600",
    ("text-", "emerald-400"): "success", ("text-", "emerald-500"): "success", ("text-", "emerald-600"): "success", ("text-", "emerald-700"): "success",
    ("text-", "green-500"): "success", ("text-", "green-600"): "success", ("text-", "green-700"): "success",
    ("text-", "red-400"): "danger", ("text-", "red-500"): "danger", ("text-", "red-600"): "danger", ("text-", "red-700"): "danger",
    ("text-", "amber-400"): "warning", ("text-", "amber-500"): "warning", ("text-", "amber-600"): "warning",
    # ---- bg ----
    ("bg-", "slate-50"): "fill-1", ("bg-", "slate-100"): "fill-2", ("bg-", "slate-200"): "fill-2",
    ("bg-", "slate-300"): "fill-3", ("bg-", "slate-400"): "fill-3", ("bg-", "slate-500"): "ink-2",
    ("bg-", "slate-600"): "ink-2", ("bg-", "slate-700"): "ink-1", ("bg-", "slate-800"): "ink-1", ("bg-", "slate-900"): "ink-1",
    ("bg-", "gray-50"): "fill-1", ("bg-", "gray-100"): "fill-2", ("bg-", "gray-200"): "fill-2",
    ("bg-", "gray-300"): "fill-3", ("bg-", "gray-400"): "fill-3", ("bg-", "gray-500"): "ink-2",
    ("bg-", "gray-600"): "ink-2", ("bg-", "gray-700"): "ink-1", ("bg-", "gray-800"): "ink-1", ("bg-", "gray-900"): "ink-1",
    ("bg-", "zinc-50"): "fill-1", ("bg-", "zinc-100"): "fill-2", ("bg-", "zinc-200"): "fill-2",
    ("bg-", "zinc-300"): "fill-3", ("bg-", "zinc-400"): "fill-3", ("bg-", "zinc-500"): "ink-2",
    ("bg-", "zinc-600"): "ink-2", ("bg-", "zinc-700"): "ink-1", ("bg-", "zinc-800"): "ink-1", ("bg-", "zinc-900"): "ink-1",
    ("bg-", "cyan-50"): "brand-50", ("bg-", "cyan-100"): "brand-100", ("bg-", "cyan-400"): "brand-400",
    ("bg-", "cyan-500"): "brand-500", ("bg-", "cyan-600"): "brand-600", ("bg-", "cyan-700"): "brand-600",
    ("bg-", "blue-50"): "brand-50", ("bg-", "blue-100"): "brand-100", ("bg-", "blue-500"): "brand-500",
    ("bg-", "blue-600"): "brand-600", ("bg-", "blue-700"): "brand-600",
    ("bg-", "emerald-50"): "success-bg", ("bg-", "emerald-100"): "success-bg",
    ("bg-", "emerald-500"): "success", ("bg-", "emerald-600"): "success", ("bg-", "emerald-700"): "success",
    ("bg-", "green-500"): "success", ("bg-", "green-600"): "success", ("bg-", "green-700"): "success",
    ("bg-", "red-50"): "danger-bg", ("bg-", "red-500"): "danger", ("bg-", "red-600"): "danger", ("bg-", "red-700"): "danger",
    ("bg-", "amber-50"): "warning-bg", ("bg-", "amber-500"): "warning", ("bg-", "amber-600"): "warning",
    # ---- border ----
    ("border-", "slate-100"): "line", ("border-", "slate-200"): "line", ("border-", "slate-300"): "line",
    ("border-", "gray-100"): "line", ("border-", "gray-200"): "line", ("border-", "gray-300"): "line",
    ("border-", "zinc-100"): "line", ("border-", "zinc-200"): "line", ("border-", "zinc-300"): "line",
    ("border-", "cyan-500"): "brand-500", ("border-", "cyan-600"): "brand-600",
    ("border-", "blue-500"): "brand-500", ("border-", "blue-600"): "brand-600",
    ("border-", "emerald-500"): "success", ("border-", "emerald-600"): "success",
    ("border-", "red-500"): "danger", ("border-", "red-600"): "danger",
    ("border-", "amber-500"): "warning",
    # ---- ring ----
    ("ring-", "cyan-500"): "brand-500", ("ring-", "emerald-500"): "success", ("ring-", "red-500"): "danger",
    ("ring-", "slate-300"): "brand-100", ("ring-", "slate-400"): "brand-100",
    ("ring-", "gray-300"): "brand-100", ("ring-", "gray-400"): "brand-100",
    # ---- divide ----
    ("divide-", "slate-200"): "line", ("divide-", "gray-200"): "line", ("divide-", "zinc-200"): "line",
    # ---- from / to / via (gradients) ----
    ("from-", "slate-50"): "fill-1", ("from-", "slate-100"): "fill-2", ("from-", "slate-500"): "ink-2",
    ("from-", "slate-700"): "ink-1", ("from-", "slate-900"): "ink-1",
    ("from-", "cyan-500"): "brand-500", ("from-", "cyan-600"): "brand-600", ("from-", "cyan-700"): "brand-600",
    ("from-", "emerald-500"): "success", ("from-", "emerald-600"): "success",
    ("to-", "slate-50"): "fill-1", ("to-", "slate-100"): "fill-2", ("to-", "slate-500"): "ink-2",
    ("to-", "slate-700"): "ink-1", ("to-", "slate-900"): "ink-1",
    ("to-", "cyan-500"): "brand-500", ("to-", "cyan-600"): "brand-600", ("to-", "cyan-700"): "brand-600",
    ("to-", "emerald-500"): "success", ("to-", "emerald-600"): "success",
    ("via-", "slate-500"): "ink-2", ("via-", "cyan-500"): "brand-500", ("via-", "emerald-500"): "success",
    # ---- fill / stroke (svg) ----
    ("fill-", "slate-400"): "ink-3", ("fill-", "slate-500"): "ink-2", ("fill-", "slate-600"): "ink-1",
    ("fill-", "cyan-500"): "brand-500", ("fill-", "emerald-500"): "success", ("fill-", "red-500"): "danger",
    ("stroke-", "slate-400"): "ink-3", ("stroke-", "slate-500"): "ink-2",
    ("stroke-", "cyan-500"): "brand-500", ("stroke-", "emerald-500"): "success", ("stroke-", "red-500"): "danger",
}

# 二次收敛：首轮未覆盖的色阶（slate-950 深色面/深色主按钮、amber/cyan/emerald/rose/sky 残留）
EXTRA = {
    # text
    ("text-", "slate-950"): "ink-1",
    ("text-", "amber-700"): "warning", ("text-", "amber-800"): "warning", ("text-", "amber-900"): "warning",
    ("text-", "cyan-300"): "brand-300", ("text-", "cyan-800"): "brand-700",
    ("text-", "emerald-800"): "success",
    ("text-", "rose-700"): "danger",
    # bg（深色主按钮保留 ink-1 深色，避免误改信息面板）
    ("bg-", "slate-950"): "ink-1",
    ("bg-", "amber-100"): "warning-bg", ("bg-", "amber-800"): "warning", ("bg-", "amber-900"): "warning",
    ("bg-", "cyan-100"): "brand-100",
    ("bg-", "emerald-100"): "success-bg", ("bg-", "emerald-800"): "success",
    ("bg-", "rose-50"): "danger-bg",
    # border
    ("border-", "slate-400"): "brand-500",
    ("border-", "amber-200"): "warning-bg",
    ("border-", "cyan-100"): "brand-100", ("border-", "cyan-300"): "brand-300", ("border-", "cyan-700"): "brand-700",
    ("border-", "emerald-100"): "success-bg", ("border-", "emerald-200"): "success-bg",
    ("border-", "rose-200"): "danger-bg",
    ("border-", "sky-500"): "brand-500",
    # ring
    ("ring-", "cyan-100"): "brand-100", ("ring-", "emerald-100"): "success-bg", ("ring-", "sky-100"): "brand-100",
    # sky（信息蓝，并入品牌蓝）
    ("text-", "sky-600"): "brand-600", ("text-", "sky-700"): "brand-700", ("text-", "sky-900"): "brand-700",
    ("bg-", "sky-50"): "brand-50", ("bg-", "sky-100"): "brand-100",
    ("bg-", "sky-500"): "brand-500", ("bg-", "sky-600"): "brand-600", ("bg-", "sky-700"): "brand-700",
    ("border-", "sky-100"): "border-brand-100", ("border-", "sky-200"): "border-brand-100",
    # violet（AI/记忆强调色，并入品牌蓝）
    ("text-", "violet-700"): "brand-700",
    ("bg-", "violet-50"): "brand-50", ("bg-", "violet-100"): "brand-100",
    ("bg-", "violet-600"): "brand-600", ("bg-", "violet-700"): "brand-700",
    # rose（危险色，并入 danger）
    ("text-", "rose-600"): "danger", ("text-", "rose-800"): "danger",
    ("bg-", "rose-100"): "danger-bg", ("border-", "rose-300"): "border-danger-bg",
    # amber 残留
    ("border-", "amber-100"): "border-warning-bg", ("bg-", "amber-700"): "warning",
    ("ring-", "amber-100"): "ring-warning-bg",
    # slate 残留（深色边框 / 代码块文字）
    ("bg-", "cyan-800"): "brand-700",
    ("ring-", "slate-200"): "ring-line",
    ("border-", "slate-700"): "border-ink-4", ("border-", "slate-950"): "border-ink-4",
    ("text-", "slate-100"): "text-ink-4",
}
MAP.update(EXTRA)

# 任意值 hex：仅处理已知可安全映射的页面底色
HEX_MAP = {
    "bg-[#f7f8fb]": "bg-fill-1",
    "bg-[#f6f8fb]": "bg-fill-1",
}

# 预编译：每个 (prefix,color) 一条带变体的正则
COMPILED = []
for (prefix, color), new in MAP.items():
    pat = re.compile(
        r"(" + VARIANT + r")(" + re.escape(prefix) + r")(" + re.escape(color) + r")\b"
    )
    COMPILED.append((pat, prefix, new))

ROUNDED_PAT = re.compile(r"(" + VARIANT + r")rounded-md\b")
HEX_PAT = re.compile(r"\b(bg|text|border|ring|from|to|via|fill|stroke)-\[#[0-9a-fA-F]{3,8}\]")

OLDS = ["slate-", "cyan-", "emerald-", "gray-", "zinc-", "neutral-", "blue-", "red-", "amber-", "green-", "sky-", "violet-", "rose-"]


def migrate_text(text):
    """返回 (new_text, change_count, hex_hits)。"""
    change = 0
    hex_hits = set()

    def _color_repl(m, new):
        return m.group(1) + m.group(2) + new

    for pat, _prefix, new in COMPILED:
        def repl(m, new=new):
            return m.group(1) + m.group(2) + new
        text, n = pat.subn(repl, text)
        change += n

    text, n = ROUNDED_PAT.subn(lambda m: m.group(1) + "rounded-lg", text)
    change += n

    for old, new in HEX_MAP.items():
        text, n = re.subn(re.escape(old), new, text)
        change += n

    for h in HEX_PAT.findall(text):
        # h 是前缀；找出完整 token
        for tok in re.findall(r"\b(bg|text|border|ring|from|to|via|fill|stroke)-\[#[0-9a-fA-F]{3,8}\]", text):
            hex_hits.add(tok)
    return text, change, sorted(hex_hits)


def scan_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return migrate_text(text)


def main():
    check_only = "--check" in sys.argv
    total_changes = 0
    changed_files = []
    hex_report = {}
    remaining_old = {}

    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith((".ts", ".tsx")):
                continue
            p = os.path.join(dirpath, fn)
            new_text, n, hexes = scan_file(p)
            rel = os.path.relpath(p, ROOT)
            if hexes:
                hex_report[rel] = hexes
            # 统计"是否仍有旧调色板残留"用于 --check 报告
            leftover = sum(1 for kw in OLDS if kw in new_text)
            if leftover:
                remaining_old[rel] = leftover
            if n > 0:
                total_changes += n
                changed_files.append((rel, n))
                if not check_only:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(new_text)

    print(f"[migrate-design-tokens] mode={'check' if check_only else 'write'}")
    print(f"  替换次数: {total_changes}")
    print(f"  改动文件: {len(changed_files)}")
    for rel, n in sorted(changed_files):
        print(f"    +{n:3d}  {rel}")
    if hex_report:
        print(f"\n  任意值 hex（未自动替换，需人工处理）: {len(hex_report)} 个文件")
        for rel, hs in hex_report.items():
            print(f"    {rel}: {hs}")
    if check_only:
        if remaining_old or hex_report:
            print(f"\n[FAIL] 仍检测到旧调色板残留: {len(remaining_old)} 文件, 任意hex: {len(hex_report)} 文件")
            sys.exit(1)
        else:
            print("\n[OK] 无旧调色板残留")
            sys.exit(0)
    else:
        # 写后再次扫描，确认是否还有残留
        if remaining_old:
            print(f"\n[WARN] 写回后仍有 {len(remaining_old)} 文件含旧调色板关键字（可能是 hex 或动态拼接）")
        print("\n完成。")


if __name__ == "__main__":
    main()
