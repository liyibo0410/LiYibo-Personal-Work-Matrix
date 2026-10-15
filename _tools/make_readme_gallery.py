# -*- coding: utf-8 -*-
r"""从 docs/assets/github/screens/*.png 生成 README 用的十模块截图墙。

用法： python -X utf8 _tools\make_readme_gallery.py
输出： docs/assets/github/modules-wall.png

纪律：只读取实拍截图，不裁剪掉信息、不合成内容、不美化数据。
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "assets", "github", "screens")
OUT = os.path.join(ROOT, "docs", "assets", "github", "modules-wall.png")

# 模块名与编号必须与 shared/config/services.json / README 第五章一致
MODULES = [
    ("p01", "P01 · AI 电商客服"),
    ("p02", "P02 · 电商运营助手 ★"),
    ("p03", "P03 · NL2SQL 问数"),
    ("p04", "P04 · RAG 知识库"),
    ("p05", "P05 · 合同审批（衡鉴）"),
    ("p06", "P06 · 数据中台"),
    ("p07", "P07 · AI 素材中心"),
    ("p08", "P08 · 直播切片"),
    ("p09", "P09 · AI 销售考核"),
    ("p10", "P10 · 模型微调平台"),
]

BG = (245, 247, 250)
CARD = (255, 255, 255)
LINE = (221, 226, 234)
INK1 = (26, 31, 43)
INK2 = (90, 100, 114)
INK3 = (138, 148, 163)
BRAND = (51, 112, 255)

MARGIN = 40
GAP = 24
COLS = 5
CELL_W = 340
IMG_H = 360
LABEL_H = 46
TITLE_H = 104
RADIUS = 10

FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_REG = r"C:\Windows\Fonts\msyh.ttc"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if not os.path.exists(path):
        raise SystemExit(f"缺少字体：{path}（中文会渲染成豆腐块，拒绝继续）")
    return ImageFont.truetype(path, size)


def rounded_card(w: int, h: int, radius: int) -> Image.Image:
    card = Image.new("RGB", (w, h), CARD)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    border = Image.new("RGB", (w, h), LINE)
    bmask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(bmask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, outline=255, width=2)
    card.paste(border, (0, 0), bmask)
    return card, mask


def main() -> int:
    rows = (len(MODULES) + COLS - 1) // COLS
    width = MARGIN * 2 + COLS * CELL_W + (COLS - 1) * GAP
    height = TITLE_H + rows * (IMG_H + LABEL_H) + (rows - 1) * GAP + MARGIN
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)

    f_title = font(FONT_BOLD, 34)
    f_sub = font(FONT_REG, 18)
    f_label = font(FONT_BOLD, 19)
    f_note = font(FONT_REG, 14)

    draw.text((MARGIN, 30), "云枢智能 CloudPivot · 十大 AI 能力模块", font=f_title, fill=INK1)
    draw.text(
        (MARGIN, 72),
        "本机 15 进程实跑界面 · 浅色态默认主题 · 2026-10-15 实拍（品牌位取自 shared/config/brand.json）",
        font=f_sub,
        fill=INK3,
    )
    draw.line([(MARGIN, TITLE_H - 14), (width - MARGIN, TITLE_H - 14)], fill=LINE, width=2)

    missing = []
    for idx, (key, label) in enumerate(MODULES):
        r, c = divmod(idx, COLS)
        x = MARGIN + c * (CELL_W + GAP)
        y = TITLE_H + r * (IMG_H + LABEL_H + GAP)

        path = os.path.join(SRC, f"{key}.png")
        if not os.path.exists(path):
            missing.append(key)
            continue

        shot = Image.open(path).convert("RGB")
        # 等比缩放铺满，重心偏上（保住顶部导航与标题，不裁掉关键信息）
        scale = max(CELL_W / shot.width, IMG_H / shot.height)
        shot = shot.resize((max(1, round(shot.width * scale)), max(1, round(shot.height * scale))), Image.LANCZOS)
        left = (shot.width - CELL_W) // 2
        top = int((shot.height - IMG_H) * 0.12)
        shot = shot.crop((left, top, left + CELL_W, top + IMG_H))

        card, mask = rounded_card(CELL_W, IMG_H, RADIUS)
        inner = shot.resize((CELL_W - 4, IMG_H - 4), Image.LANCZOS)
        card.paste(inner, (2, 2))
        canvas.paste(card, (x, y), mask)

        draw.text((x + 4, y + IMG_H + 6), label, font=f_label, fill=INK1)
        draw.text((x + 4, y + IMG_H + 28), "本机实拍 · 浅色态", font=f_note, fill=INK3)

    canvas.save(OUT, "PNG", optimize=True)
    size = os.path.getsize(OUT)
    print(f"saved {OUT}")
    print(f"size  {width} x {height}")
    print(f"bytes {size} ({size / 1024:.1f} KB)")
    if missing:
        print("MISSING SCREENSHOTS:", missing)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())