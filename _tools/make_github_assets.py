#!/usr/bin/env python -X utf8
# -*- coding: utf-8 -*-
"""生成并自检 GitHub 展示用视觉资产（离线，不访问网络）。

用法（在仓库根目录）：
    python -X utf8 _tools\\make_github_assets.py              # 重绘 PNG + 自检
    python -X utf8 _tools\\make_github_assets.py --check-only # 只自检，不重绘

产物（全部落在 docs/assets/github/）：
    banner.svg          1280x320  浅色头图（README 顶部）
    banner-dark.svg     1280x320  深色头图（README 顶部，深色主题读者）
    social-preview.svg  1280x640  社交预览（源文件）
    social-preview.png  1280x640  社交预览（GitHub「社交预览」上传用，Pillow 直绘）

本脚本做三件事：
  1. 用 Pillow 从零重绘 social-preview.png（2 倍超采样后降采样），打印尺寸与字节数；
  2. 校验三张 SVG 的 width/height/viewBox、必需文案、以及安全清洗红线
     （不得含 <script>/<foreignObject>/<image>/<style>/@import/外链 href）、
     可访问性（role="img" + <title> + <desc>）、字体属性列表、UTF-8 无 BOM；
  3. 逐条文本估算宽度并按锚点算出左右边界，断言不越界（≥24px 边距）。

文本宽度估算口径（本仓库统一的保守口径）：
    中文/全角字符 = font-size × 1.0      ASCII 英数字与半角符号 = font-size × 0.55
    U+00B7 中点按 1.0 计（中文字体里它是全角宽度）—— 估算值 ≥ 真实渲染宽度。

字体：默认用 Windows 自带 Microsoft YaHei（C:\\Windows\\Fonts\\msyh.ttc 与 msyhbd.ttc）。
      候选字体逐个探测（存在 → 可加载 → 汉字能渲染出互不相同的字模），
      全部不可用时**直接报错退出**，绝不静默输出豆腐块。
      可用环境变量 CP_ASSET_FONT_REG / CP_ASSET_FONT_BOLD 覆盖。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ───────────────────────────── 常量 ─────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets" / "github"

BANNER_W, BANNER_H = 1280, 320
SOCIAL_W, SOCIAL_H = 1280, 640
S = 2  # 超采样倍数：2 倍绘制后降采样，保证中文小字不发毛

MIN_MARGIN = 24          # 文本距画布边缘的最小留白（px）
MAX_PNG_BYTES = 400 * 1024

FONT_FAMILY_ATTR = (
    "font-family=\"'Microsoft YaHei','PingFang SC',Inter,-apple-system,"
    "'Segoe UI',sans-serif\""
)

REG_CANDIDATES = [
    os.environ.get("CP_ASSET_FONT_REG", ""),
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]
BOLD_CANDIDATES = [
    os.environ.get("CP_ASSET_FONT_BOLD", ""),
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyhbd.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

# 汉字字模探测用字符：缺字时这些字符会全部渲染成同一个 .notdef 方框
CJK_PROBE = "李奕波个人作品矩阵电商运营模块架构数据层"

# 设计令牌（唯一真源 shared/ui-kit/tokens.css）
C_BG        = "#FFFFFF"   # 社交预览白底
C_GRID      = "#EEF0F4"   # #DDE2EA 以 0.5 透明度压在纯白上的等效色
C_LINE      = "#DDE2EA"
C_INK1      = "#1A1F2B"
C_INK2      = "#5A6472"
C_INK3      = "#8A94A3"
C_BRAND     = "#3370FF"
C_CHIP      = "#F5F7FA"
C_L0        = "#98A2B3"   # 图表序列 6 号（中性色）
C_L1        = "#85ACFF"   # 品牌蓝 · 浅
C_L2        = "#5A8AFF"   # 品牌蓝 · 中
C_L3        = "#3370FF"   # 品牌蓝（唯一强调色）

# ───────────────────────── 字体探测与加载 ─────────────────────────

_font_cache: dict[tuple[str, int], object] = {}
_font_paths: dict[str, str] = {}


def _probe(path: str, size: int) -> tuple[bool, str]:
    """探测一个字体文件能否渲染出互不相同的汉字字模。"""
    if not path or not Path(path).is_file():
        return False, "文件不存在"
    try:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype(path, size)
    except Exception as exc:  # noqa: BLE001
        return False, f"加载失败：{exc}"
    seen: dict[bytes, str] = {}
    for ch in CJK_PROBE:
        canvas = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(canvas).text((size // 2, size // 2), ch, font=font, fill=255)
        bbox = canvas.getbbox()
        if bbox is None:
            return False, f"汉字 “{ch}” 字模为空"
        raw = canvas.tobytes()
        if raw in seen:
            return False, f"汉字 “{seen[raw]}” 与 “{ch}” 字模完全相同（疑似 .notdef 豆腐块）"
        seen[raw] = ch
    return True, "ok"


def resolve_fonts() -> None:
    """选定 regular / bold 字体文件；不可用则明确报错退出。"""
    for weight, candidates in (("regular", REG_CANDIDATES), ("bold", BOLD_CANDIDATES)):
        tried: list[str] = []
        for path in candidates:
            ok, why = _probe(path, 40)
            tried.append(f"    - {path or '(未设置)'} → {why}")
            if ok:
                _font_paths[weight] = path
                break
        else:
            sys.stderr.write(
                f"[FATAL] 找不到可用于 {weight} 的中文字体，拒绝生成（否则会静默输出豆腐块）。\n"
                f"  已尝试：\n" + "\n".join(tried) + "\n"
                "  解决：安装 Microsoft YaHei（Windows 自带 C:\\Windows\\Fonts\\msyh.ttc），"
                "或用环境变量 CP_ASSET_FONT_REG / CP_ASSET_FONT_BOLD 指向可用的中文字体。\n"
            )
            raise SystemExit(2)


def font(weight: str, size: int):
    key = (weight, size)
    if key not in _font_cache:
        from PIL import ImageFont
        _font_cache[key] = ImageFont.truetype(_font_paths[weight], size)
    return _font_cache[key]


# ───────────────────── 文本宽度估算 / 排版辅助 ─────────────────────

def _is_wide(ch: str) -> bool:
    cp = ord(ch)
    if cp == 0xB7:                      # · 中点：中文字体里按全角计
        return True
    if 0x2E80 <= cp <= 0x9FFF:          # CJK 部首扩展 ~ 统一表意文字
        return True
    if 0x3000 <= cp <= 0x303F:          # CJK 标点（。，、〈〉…）
        return True
    if 0xFE30 <= cp <= 0xFE4F:          # CJK 兼容形式
        return True
    if 0xFF00 <= cp <= 0xFFEF:          # 全角 ASCII / 全角符号
        return True
    return False


def est_width(text: str, size: float) -> float:
    """保守估算宽度：中文 1.0em、英数 0.55em（≥ 真实渲染宽度）。"""
    return sum(1.0 if _is_wide(c) else 0.55 for c in text) * size


# ─────────────────────────── PNG 重绘 ───────────────────────────

def draw_social_preview(dest: Path) -> tuple[int, int, int]:
    """从零重绘 social-preview.png。坐标与 social-preview.svg 一一对应。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (SOCIAL_W * S, SOCIAL_H * S), C_BG)
    d = ImageDraw.Draw(img)

    def px(v: float) -> int:
        return int(round(v * S))

    def rect(x, y, w, h, r, fill, outline=None, lw=1):
        box = [px(x), px(y), px(x + w) - 1, px(y + h) - 1]
        if outline:
            d.rounded_rectangle(box, radius=px(r), fill=fill, outline=outline, width=max(1, px(lw)))
        else:
            d.rounded_rectangle(box, radius=px(r), fill=fill)

    def line(x1, y1, x2, y2, color=C_LINE, lw=1):
        d.line([(px(x1), px(y1)), (px(x2), px(y2))], fill=color, width=max(1, px(lw)))

    def text(x, y, s, size, fill, weight="regular", anchor="ls"):
        d.text((px(x), px(y)), s, font=font(weight, px(size)), fill=fill, anchor=anchor)

    # 极淡网格纹理（64px 栅格）
    for x in range(64, SOCIAL_W, 64):
        line(x, 0, x, SOCIAL_H - 1, C_GRID, 1)
    for y in range(64, SOCIAL_H, 64):
        line(0, y, SOCIAL_W - 1, y, C_GRID, 1)

    # 顶部强调色标线
    d.rectangle([0, 0, px(SOCIAL_W) - 1, px(6) - 1], fill=C_BRAND)

    # 品牌区
    rect(80, 72, 48, 48, 12, C_BRAND)
    text(104, 106, "CP", 20, "#FFFFFF", "bold", "ms")
    text(144, 102, "李奕波个人作品矩阵 Li Yibo's Personal Portfolio", 22, C_INK1, "bold")
    text(144, 127, "AI 电商运营中台", 14, C_INK3)
    text(1200, 102, "本机 15 进程实跑 · 界面截图见仓库 README", 15, C_INK3, anchor="rs")

    # 四层架构胶囊（L0 → L3）
    chips = [
        (80, 126, C_L0, "L0 数据中台"),
        (218, 126, C_L1, "L1 模型微调"),
        (356, 112, C_L2, "L2 能力层"),
        (480, 112, C_L3, "L3 应用层"),
    ]
    for cx, cw, dot, label in chips:
        rect(cx, 160, cw, 34, 17, C_CHIP, C_LINE)
        d.ellipse([px(cx + 18 - 4), px(173), px(cx + 18 + 4) - 1, px(181) - 1], fill=dot)
        text(cx + 30, 182, label, 14, C_INK2)

    # 主标题与副标题
    text(80, 272, "十个 AI 能力模块，合并成一套统一系统", 50, C_INK1, "bold")
    text(80, 316, "微前端外壳统一挂载，非单体合并 · 跨模块真实 HTTP 调用 4 条链路", 20, C_INK2)

    # 实测数字块
    line(80, 356, 1200, 356)
    for x in (340, 620, 900):
        line(x, 386, x, 492)
    metrics = [
        (80, "10", "业务模块"),
        (360, "4", "层架构 · 6 条 ADR"),
        (640, "15", "受管进程"),
        (920, "731", "pytest passed"),
    ]
    for mx, num, label in metrics:
        text(mx, 440, num, 46, C_BRAND, "bold")
        text(mx, 480, label, 16, C_INK2)

    # 页脚
    line(80, 540, 1200, 540)
    text(80, 584, "李奕波 · 独立开发 · 全栈工程", 17, C_INK2)
    text(1200, 584, "github.com/liyibo0410/yunshu-ai-portfolio", 17, C_INK3, anchor="rs")

    out = img.resize((SOCIAL_W, SOCIAL_H), Image.Resampling.LANCZOS)
    out.save(dest, format="PNG", optimize=True)
    return out.size[0], out.size[1], dest.stat().st_size


# ─────────────────────────── SVG 自检 ───────────────────────────

REPO_URL = "github.com/liyibo0410/yunshu-ai-portfolio"

BANNER_NODES = [
    "CP",
    "李奕波个人作品矩阵 Li Yibo's Personal Portfolio",
    "AI 电商运营中台 · 十个 AI 能力模块，一套统一系统",
    "10 模块", "4 层架构", "15 受管进程", "731 passed",
    "架构分层",
    "L3 应用层", "L2 能力层", "L1 模型微调", "L0 数据中台",
    "四个跨模块真实调用 · 6 条 ADR",
    REPO_URL,
]

SOCIAL_NODES = [
    "CP",
    "李奕波个人作品矩阵 Li Yibo's Personal Portfolio",
    "AI 电商运营中台",
    "本机 15 进程实跑 · 界面截图见仓库 README",
    "L0 数据中台", "L1 模型微调", "L2 能力层", "L3 应用层",
    "十个 AI 能力模块，合并成一套统一系统",
    "微前端外壳统一挂载，非单体合并 · 跨模块真实 HTTP 调用 4 条链路",
    "10", "业务模块",
    "4", "层架构 · 6 条 ADR",
    "15", "受管进程",
    "731", "pytest passed",
    "李奕波 · 独立开发 · 全栈工程",
    REPO_URL,
]

SVG_SPECS = [
    {
        "file": "banner.svg",
        "size": (BANNER_W, BANNER_H),
        "nodes": BANNER_NODES,
        "must": [
            "李奕波个人作品矩阵 Li Yibo's Personal Portfolio",
            "AI 电商运营中台",
            "十个 AI 能力模块，一套统一系统",
            "10 模块", "4 层架构", "15 受管进程", "731 passed",
            "L3 应用层", "L2 能力层", "L1 模型微调", "L0 数据中台",
            "四个跨模块真实调用 · 6 条 ADR", REPO_URL,
        ],
    },
    {
        "file": "banner-dark.svg",
        "size": (BANNER_W, BANNER_H),
        "nodes": BANNER_NODES,
        "must": [
            "李奕波个人作品矩阵 Li Yibo's Personal Portfolio",
            "AI 电商运营中台",
            "十个 AI 能力模块，一套统一系统",
            "10 模块", "4 层架构", "15 受管进程", "731 passed",
            "L3 应用层", "L2 能力层", "L1 模型微调", "L0 数据中台",
            "四个跨模块真实调用 · 6 条 ADR", REPO_URL,
            "#151A23", "#1E2430", "#2C3442", "#F2F5F9", "#A7B0BE",
        ],
    },
    {
        "file": "social-preview.svg",
        "size": (SOCIAL_W, SOCIAL_H),
        "nodes": SOCIAL_NODES,
        "must": [
            "李奕波个人作品矩阵 Li Yibo's Personal Portfolio",
            "AI 电商运营中台",
            "十个 AI 能力模块，合并成一套统一系统",
            "微前端外壳统一挂载，非单体合并",
            "业务模块", "pytest passed",
            "李奕波", "独立开发", REPO_URL,
        ],
    },
]

FORBIDDEN = [
    ("<script", "内联脚本（camo 清洗会剔除，且属安全红线）"),
    ("<foreignObject", "foreignObject（HTML 混排，渲染不可靠）"),
    ("<image", "位图引用（会引入外链图片）"),
    ("<style", "内联样式块（部分清洗器会剔除）"),
    ("@import", "CSS 外链导入"),
    ("<use", "外部符号引用"),
    ("xlink:href", "旧式外链引用"),
    ("http://www.w3.org/1999/xlink", "xlink 命名空间"),
]

TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)

# 封面（头图 + 社交预览）一律不放任何入口：不放 IP、不放端口、不放演示 URL，
# 也不用「在线演示」这类必须真有一个可点入口才成立的措辞。
# 入口只写在仓库 README 正文与 docs/assets/github/online-demo.md，并标注为按需开启。
# 下面四条常驻检查就是这条决定的执行体 —— 想加回入口，先把这里改掉。
ENTRY_PATTERNS = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "IPv4 地址"),
    (re.compile(r"https?://(?!www\.w3\.org/)"), "外链 URL（xmlns 命名空间除外）"),
    (re.compile(r":\d{2,5}(?=[/\s\"'])"), "带端口的地址"),
    (re.compile(r"在线演示|在线 Demo|live demo", re.I), "需入口才成立的措辞"),
]


def _read_svg(path: Path) -> tuple[str, str | None]:
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig"), "UTF-8 带 BOM"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return "", f"不是合法 UTF-8：{exc}"


def check_svg(spec: dict) -> list[tuple[str, bool | None, str]]:
    """返回 (检查项, 是否通过 or None 表示信息项, 说明) 列表。"""
    path = ASSETS / spec["file"]
    rows: list[tuple[str, bool | None, str]] = []
    tag = spec["file"]

    if not path.is_file():
        rows.append((f"{tag} 存在", False, f"缺文件：{path}"))
        return rows
    src, enc_problem = _read_svg(path)
    rows.append((f"{tag} · UTF-8 无 BOM", enc_problem is None, enc_problem or "解码正常"))

    w, h = spec["size"]
    wm = re.search(r'\bwidth\s*=\s*"(\d+)"', src)
    hm = re.search(r'\bheight\s*=\s*"(\d+)"', src)
    vm = re.search(r'\bviewBox\s*=\s*"([^"]*)"', src)
    ok = (wm and hm and int(wm.group(1)) == w and int(hm.group(1)) == h)
    rows.append((f"{tag} · 尺寸 {w}x{h}", bool(ok),
                 f'width={wm.group(1) if wm else "?"} height={hm.group(1) if hm else "?"}'))

    # XML 良构性：浏览器与 GitHub 的渲染器都会在解析失败时整张放弃
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(src)
        wf_note = f"根元素 <{root.tag.split('}')[-1]}>，子节点 {len(list(root))} 个"
        wf_ok = True
    except Exception as exc:  # noqa: BLE001
        wf_ok, wf_note = False, f"{type(exc).__name__}: {exc}"
    rows.append((f"{tag} · XML 良构（可被解析）", wf_ok, wf_note))
    rows.append((f"{tag} · viewBox", bool(vm) and vm.group(1).split() == ["0", "0", str(w), str(h)],
                 vm.group(1) if vm else "缺失"))

    missing = [s for s in spec["must"] if s not in src]

    # 逐条文本边界
    nodes: list[str] = []
    problems: list[str] = []
    checked = 0
    for attrs, body in TEXT_RE.findall(src):
        a = dict(ATTR_RE.findall(attrs))
        body = re.sub(r"<[^>]+>", "", body).strip()
        if not body:
            continue
        nodes.append(body)
        if "x" not in a:
            continue
        size = float(a.get("font-size", "16"))
        anchor = a.get("text-anchor", "start")
        x = float(a["x"])
        y = float(a.get("y", "0"))
        ls = float(a.get("letter-spacing", "0"))
        wide = est_width(body, size) + ls * max(0, len(body) - 1)
        if anchor == "end":
            left, right = x - wide, x
        elif anchor == "middle":
            left, right = x - wide / 2, x + wide / 2
        else:
            left, right = x, x + wide
        checked += 1
        if left < MIN_MARGIN or right > w - MIN_MARGIN:
            problems.append(f"“{body}” 估算区间 [{left:.0f},{right:.0f}] 越界")
        if y - size < 0 or y + 0.3 * size > h:
            problems.append(f"“{body}” 基线 y={y:g} 垂直越界")

    missing_nodes = [s for s in spec.get("nodes", []) if s not in nodes]
    rows.append((f"{tag} · 必需文案(整串) {len(spec['must'])} 条", not missing,
                 "全部命中" if not missing else "缺：" + " / ".join(missing)))
    rows.append((f"{tag} · 关键文本节点 {len(spec.get('nodes', []))} 条",
                 not missing_nodes,
                 f"文本节点共 {len(nodes)} 条，全部命中" if not missing_nodes
                 else "缺：" + " / ".join(missing_nodes)))

    hits = [f"{tok}（{why}）" for tok, why in FORBIDDEN if tok in src]
    rows.append((f"{tag} · 安全红线（无脚本/外链）", not hits, "干净" if not hits else "命中：" + "；".join(hits)))

    # XML 语法：注释体内出现 “--” 会让解析器直接报错（浏览器与 GitHub 都不渲染）
    bad_comments = [c.strip()[:40] for c in COMMENT_RE.findall(src) if "--" in c]
    rows.append((f"{tag} · XML 注释无 “--”", not bad_comments,
                 "注释合法" if not bad_comments else "非法注释：" + " / ".join(bad_comments)))

    # 封面不放任何入口（机主 2026-10-15 决定）
    entries = []
    for pat, why in ENTRY_PATTERNS:
        for hit in pat.findall(src):
            entries.append(f"{why}={hit if isinstance(hit, str) else hit}")
    rows.append((f"{tag} · 封面不含入口地址", not entries,
                 "无 IP / 端口 / 演示 URL" if not entries else "命中：" + "；".join(entries)))

    a11y = ('role="img"' in src, "<title>" in src, "<desc>" in src)
    rows.append((f"{tag} · 可访问性 role/title/desc", all(a11y),
                 f"role={'Y' if a11y[0] else 'N'} title={'Y' if a11y[1] else 'N'} desc={'Y' if a11y[2] else 'N'}"))

    rows.append((f"{tag} · 字体属性列表", FONT_FAMILY_ATTR in src,
                 "命中预期 font-family 列表" if FONT_FAMILY_ATTR in src else "font-family 与预期不一致"))

    rows.append((f"{tag} · 文本不越界（{checked} 条）", not problems,
                 "全部落在 ≥24px 边距内" if not problems else "；".join(problems)))
    return rows


# ─────────────────────────── 主流程 ───────────────────────────

def main() -> int:
    check_only = "--check-only" in sys.argv
    ASSETS.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("李奕波个人作品矩阵 · GitHub 视觉资产生成与自检")
    print("=" * 78)

    resolve_fonts()
    print(f"字体 regular : {_font_paths['regular']}")
    print(f"字体 bold    : {_font_paths['bold']}")

    rows: list[tuple[str, bool | None, str]] = []

    png = ASSETS / "social-preview.png"
    if check_only:
        rows.append(("social-preview.png 重绘", None, "--check-only：跳过重绘"))
    else:
        w, h, nbytes = draw_social_preview(png)
        print(f"重绘 social-preview.png → {w}x{h} · {nbytes:,} 字节（{nbytes / 1024:.1f} KB）")
        rows.append((f"social-preview.png 生成 {w}x{h}", (w, h) == (SOCIAL_W, SOCIAL_H),
                     f"{nbytes:,} 字节"))

    # PNG 校验
    if png.is_file():
        from PIL import Image
        with Image.open(png) as im:
            size = im.size
            im_rgb = im.convert("RGB")
            lastx, lasty = SOCIAL_W - 1, SOCIAL_H - 1
            samples = [(40, 250), (1240, 250), (620, 610), (40, 610), (lastx - 40, lasty - 20)]
            colors = im_rgb.getcolors(maxcolors=1 << 24) or []
            blank = 0 < len(colors) < 40
            top = sorted(colors, reverse=True)[:1]
            dominant = top[0][1] if top else None
            dom_share = (top[0][0] / (SOCIAL_W * SOCIAL_H)) if top else 0.0
        rows.append(("social-preview.png 尺寸 1280x640", size == (SOCIAL_W, SOCIAL_H), str(size)))
        nbytes = png.stat().st_size
        rows.append(("social-preview.png ≤ 400 KB", nbytes <= MAX_PNG_BYTES, f"{nbytes:,} 字节"))
        bg_ok_note = "采样点均取自无网格线/无文字的纯背景区"  # noqa: F841
        ok_bg = dominant == (255, 255, 255) and dom_share > 0.60 and \
            all(im_rgb.getpixel(p) == (255, 255, 255) for p in samples)
        rows.append(("social-preview.png 底色为白", ok_bg,
                     f"主色 {dominant} 占比 {dom_share:.0%}；采样点 "
                     + " ".join(str(im_rgb.getpixel(p)) for p in samples)))
        rows.append(("social-preview.png 非空白图", not blank, "色彩数充足" if not blank else "几乎纯色"))
        # 中文渲染校验：把画布上出现过的字重跑一次字模探测，确认不是豆腐块
        ok_reg, why_reg = _probe(_font_paths["regular"], 40)
        ok_bold, why_bold = _probe(_font_paths["bold"], 40)
        rows.append(("social-preview.png 中文非豆腐块", ok_reg and ok_bold,
                     f"regular={why_reg} bold={why_bold}"))
    else:
        rows.append(("social-preview.png 存在", False, f"缺文件：{png}"))

    for spec in SVG_SPECS:
        rows.extend(check_svg(spec))

    print()
    print("-" * 78)
    print(f"{'检查项':<44}{'结果':<8}说明")
    print("-" * 78)
    failed = 0
    for name, ok, note in rows:
        mark = "INFO" if ok is None else ("PASS" if ok else "FAIL")
        if ok is False:
            failed += 1
        print(f"{name:<44}{mark:<8}{note}")
    print("-" * 78)

    for spec in SVG_SPECS:
        p = ASSETS / spec["file"]
        if p.is_file():
            print(f"  {spec['file']:<22}{spec['size'][0]}x{spec['size'][1]}  {p.stat().st_size:,} 字节")
    if png.is_file():
        print(f"  {'social-preview.png':<22}{SOCIAL_W}x{SOCIAL_H}  {png.stat().st_size:,} 字节")
    print("-" * 78)
    print(f"合计 {len(rows)} 项检查 · FAIL {failed} 项")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())