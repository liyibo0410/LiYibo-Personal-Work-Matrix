"""把各页 .slide 里的 notes 台词写入 .pptx 的演讲者备注页，并导出逐字演讲稿 Markdown。

背景：当前版本的页面编译只生成备注母版，不会把每页 notes 落成备注页，
因此这里用标准 OOXML 方式在每页的备注页里补一个正文占位符并写入台词。

用法：
    python scripts_notes_export.py
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn

PROJ = Path(__file__).resolve().parent
PPTX = PROJ / "客户汇报.pptx"
SLIDES = PROJ / "slides"
OUT_MD = PROJ.parent / "06-客户汇报演讲稿.md"

TITLES = {
    1: "封面 · AI 电商运营助手",
    2: "五段叙事 · 目录",
    3: "痛点与目标",
    4: "技术栈与分层架构",
    5: "一次请求的生命周期",
    6: "难点一 · 受控工具网关",
    7: "难点二 · 人工审批 + 断点恢复",
    8: "难点三 · 重复消息下的可靠执行",
    9: "工程化与自研增量",
    10: "验收方法",
    11: "验收结果",
    12: "关键证据 · 四条实测输出",
    13: "安全与合规边界",
    14: "交付边界与后续规划",
}

NSDECL = (
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
)


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def extract_notes(path: Path) -> str:
    """从 .slide 源码里抽出 notes 模板字符串的内容。"""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"notes=\{\s*`(.*?)`\s*\}", text, re.S)
    if not match:
        raise SystemExit(f"未找到 notes：{path}")
    lines = [line.strip() for line in match.group(1).splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def notes_body_sp(text: str, shape_id: int):
    """构造一个 notes 正文占位符，段落按换行切分。"""
    paras = "".join(
        f'<a:p><a:pPr/><a:r><a:rPr lang="zh-CN"/><a:t>{esc(line)}</a:t></a:r></a:p>'
        for line in text.split("\n")
        if line.strip()
    )
    xml = (
        f"<p:sp {NSDECL}>"
        "<p:nvSpPr>"
        f'<p:cNvPr id="{shape_id}" name="Notes Placeholder {shape_id}"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="body" idx="1"/></p:nvPr>'
        "</p:nvSpPr>"
        "<p:spPr/>"
        f'<p:txBody><a:bodyPr/><a:lstStyle/>{paras}</p:txBody>'
        "</p:sp>"
    )
    return parse_xml(xml)


def main() -> int:
    prs = Presentation(str(PPTX))
    notes_map: dict[int, str] = {}

    if len(prs.slides) != 14:
        raise SystemExit(f"页数不是 14：{len(prs.slides)}")

    for idx in range(1, 15):
        note = extract_notes(SLIDES / f"{idx:02d}.slide")
        notes_map[idx] = note
        slide = prs.slides[idx - 1]
        notes_slide = slide.notes_slide
        sp_tree = notes_slide._element.find(qn("p:cSld")).find(qn("p:spTree"))
        # 清掉可能存在的旧正文占位符，避免重复
        for sp in list(sp_tree.findall(qn("p:sp"))):
            ph = sp.find(qn("p:nvSpPr"))
            if ph is not None and ph.find(qn("p:nvPr")) is not None:
                if ph.find(qn("p:nvPr")).find(qn("p:ph")) is not None:
                    sp_tree.remove(sp)
        sp_tree.append(notes_body_sp(note, 2))
        print(f"slide {idx:02d}: notes {len(note)} 字")

    prs.save(str(PPTX))

    total = sum(len(v) for v in notes_map.values())
    lines = [
        "# 答辩 PPT 演讲稿（10 分钟 · 逐字稿）",
        "",
        "> 与 `客户汇报.pptx` 的演讲者备注一一对应（14 页）。",
        "> 演示时打开 PowerPoint 的「演讲者视图」即可照读；本文档用于打印或背诵。",
        "",
        f"- 全文约 {total} 字；按中文答辩语速 240 字/分钟计，约 **{total / 240:.1f} 分钟**。",
        "",
        "---",
        "",
    ]
    for idx in range(1, 15):
        lines.append(f"## 第 {idx} 页 · {TITLES[idx]}")
        lines.append("")
        for para in notes_map[idx].split("\n"):
            para = para.strip()
            if para:
                lines.append(para)
                lines.append("")
        lines.append(f"*（本页 {len(notes_map[idx])} 字）*")
        lines.append("")
        lines.append("---")
        lines.append("")
    with io.open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(f"共 {len(notes_map)} 页备注，合计 {total} 字；演讲稿 -> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
