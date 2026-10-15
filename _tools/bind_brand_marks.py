"""给各静态模块的品牌位挂上「可换 logo / 可改名」钩子。

现状：只有 shell 与 P07 的 logo 绑了 brand.json，其余模块的 logo 是写死的，
用户在「品牌定制」里换图后只有外壳变、模块不变。
做法：在既有 logo 槽位上加 class="cp-brandmark" data-cp-brand="logo"，
由 ui-kit.js 的 CP.applyBrand 按 shared/config/brand.json 写入图片或字母标。
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKUP = ROOT / "_runtime" / "brandmark-backup"

MARK = '<div class="cp-brandmark" data-cp-brand="logo">YD</div>'

PLAN: dict[str, list[tuple[str, str, int]]] = {
    # P06：logo 放在模块名上方
    "projects/p06-data-platform/web/index.html": [
        ('    <div class="sidebar-header">\n      <h1 data-cp-brand="company">李奕波个人作品矩阵</h1>',
         '    <div class="sidebar-header">\n      ' + MARK + '\n      <h1 data-cp-brand="company">李奕波个人作品矩阵</h1>', 1),
    ],
    # P08：侧栏标题块
    "projects/p08-live-clip/web/index.html": [
        ('    <div class="sidebar-logo">\n      <h1>P08 直播切片</h1>',
         '    <div class="sidebar-logo">\n      ' + MARK + '\n      <h1>P08 直播切片</h1>', 1),
    ],
    # P09：h1 本身就是品牌名，logo 另起一行
    "projects/p09-ai-sales-assessment/web/index.html": [
        ('    <div class="sidebar-logo">\n      <h1 data-cp-brand="company">李奕波个人作品矩阵</h1>',
         '    <div class="sidebar-logo">\n      ' + MARK + '\n      <h1 data-cp-brand="company">李奕波个人作品矩阵</h1>', 1),
    ],
    # P10
    "projects/p10-model-finetune/web/index.html": [
        ('    <div class="logo">\n      <h1>P10 微调平台</h1>',
         '    <div class="logo">\n      ' + MARK + '\n      <h1>P10 微调平台</h1>', 1),
    ],
    # P04 管理台：把自带的图标槽位变成可替换的品牌位（SVG 作为 JS 生效前的兜底）
    "projects/p04-rag-knowledge-base/web/page/console.html": [
        ('                <div class="sidebar-logo-icon">',
         '                <div class="sidebar-logo-icon cp-brandmark" data-cp-brand="logo">', 1),
    ],
    # P04 问答页：原本是个空的 .logo 容器
    "projects/p04-rag-knowledge-base/web/page/chat.html": [
        ('        <div class="logo"></div>',
         '        <div class="logo cp-brandmark" data-cp-brand="logo">YD</div>', 1),
    ],
    # 作品集站：顶栏与页脚的品牌位改名可定制
    "01-portfolio/index.html": [
        ('      <span class="cp-logo">云</span>',
         '      <span class="cp-logo" data-cp-brand="logo">云</span>', 1),
        ('        <span class="cp-brand-name">李奕波个人作品矩阵 <span class="text-[var(--cp-brand)]">Li Yibo's Personal Portfolio</span></span>',
         '        <span class="cp-brand-name"><span data-cp-brand="company">李奕波个人作品矩阵</span> '
         '<span class="text-[var(--cp-brand)]" data-cp-brand="name_en">Li Yibo's Personal Portfolio</span></span>', 1),
        ('    <p>李奕波个人作品矩阵 Li Yibo's Personal Portfolio · 全栈 AI 作品集</p>',
         '    <p><span data-cp-brand="company">李奕波个人作品矩阵</span> <span data-cp-brand="name_en">Li Yibo's Personal Portfolio</span> · 全栈 AI 作品集</p>', 1),
        ('<body class="cp-app">',
         '<body class="cp-app" data-cp-brand-src="../shared/config/brand.json">', 1),
        ('<script src="https://cdn.tailwindcss.com"></script>',
         '<script src="https://cdn.tailwindcss.com"></script>\n<script src="../shared/ui-kit/ui-kit.js"></script>', 1),
    ],
    # 手机速览画廊
    "mobile-gallery/v2/index.html": [
        ('    <h1>李奕波个人作品矩阵 · AI 电商运营中台</h1>',
         '    <h1><span data-cp-brand="company">李奕波个人作品矩阵</span> · <span data-cp-brand="subtitle">AI 电商运营中台</span></h1>', 1),
        ('<body>',
         '<body data-cp-brand-src="../../shared/config/brand.json">', 1),
        ('<script>',
         '<script src="../../shared/ui-kit/ui-kit.js"></script>\n<script>', 1),
    ],
}


def main() -> int:
    problems: list[str] = []
    touched = 0
    for rel, edits in sorted(PLAN.items()):
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel} 不存在")
            continue
        text = path.read_text(encoding="utf-8")
        before = text
        for old, new, want in edits:
            got = text.count(old)
            if got != want:
                problems.append(f"{rel}：片段「{old.strip()[:46]}」命中 {got} 次，期望 {want} 次 —— 跳过该处")
                continue
            text = text.replace(old, new)
        if text != before:
            dst = BACKUP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(path, dst)
            path.write_text(text, encoding="utf-8", newline="")
            touched += 1
    sys.stdout.write(f"挂上品牌钩子的文件：{touched} 个\n")
    for p in problems:
        sys.stdout.write("  ! " + p + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
