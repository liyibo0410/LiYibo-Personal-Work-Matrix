"""P07 AI 生成：文案与视频脚本真调 LLM；图片为程序化绘制的规格卡片（不出网）。

边界（写进接口响应与 UI）：
- `copy` / `video`：分镜与文案由 `shared/llm-gateway` 真实生成，凭证不可用时退回规则模板并标 `source=rule`；
- `image`：**不是 AI 出图**，是用 Pillow 按投放规格绘制的占位卡片（品牌色 + 文案），
  目的是把「生成 → 落库 → 预览 → 检索」这条链路跑成真闭环，而不是给一张外链假图。
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from app import config
from app.services import llm, media

# 各类型的投放规格（宽, 高）与卡片主色
_SPEC = {
    "image": (800, 800, "#3370FF"),
    "video": (1080, 1920, "#7B5CFA"),
    "copy": (1200, 400, "#16A34A"),
}


def render_spec_card(prompt: str, asset_type: str, style: str, out_path: Path) -> dict[str, int]:
    """按投放规格绘制素材卡片，返回真实宽高。"""
    from PIL import Image, ImageDraw

    w, h, color = _SPEC.get(asset_type, _SPEC["image"])
    img = Image.new("RGB", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    band_h = int(h * 0.62)
    draw.rectangle([0, 0, w, band_h], fill=color)
    draw.line([0, band_h, w, band_h], fill="#DDE2EA", width=max(2, w // 300))

    title_font = media.load_font(max(20, w // 18))
    small_font = media.load_font(max(14, w // 30))

    def wrap(text: str, width_chars: int) -> list[str]:
        return [text[i:i + width_chars] for i in range(0, len(text), width_chars)][:4]

    lines = wrap(prompt[:60], max(6, w // (max(20, w // 18))))
    y = int(band_h * 0.28)
    for line in lines:
        draw.text((int(w * 0.08), y), line, fill="#FFFFFF", font=title_font)
        y += int(title_font.size * 1.5)

    meta = f"{style} · {w}x{h} · programmatic card (not AI-drawn)"
    draw.text((int(w * 0.08), band_h + int(h * 0.06)), meta, fill="#5A6472", font=small_font)
    draw.text((int(w * 0.08), band_h + int(h * 0.16)),
              f"CloudPivot P07 {datetime.now():%Y-%m-%d %H:%M}", fill="#8A94A3", font=small_font)
    img.save(out_path, "PNG")
    return {"width": w, "height": h}


def _rule_copy(prompt: str, style: str) -> dict[str, Any]:
    return {
        "title": f"{prompt[:18]}｜{'商业' if style == 'commercial' else style}主推文案",
        "subtitle": "品质用料 · 场景实拍 · 一键投放",
        "bullets": [f"{prompt[:10]}核心卖点前置", "场景化痛点演绎", "促销钩子收口"],
        "cta": "立即抢购",
        "tags": ["文案", "规则模板"],
    }


def _rule_script(prompt: str) -> dict[str, Any]:
    return {
        "title": f"{prompt[:18]}｜15s 竖版脚本",
        "total_seconds": 15,
        "scenes": [
            {"time": "0-3s", "shot": "产品特写", "voice": f"{prompt[:12]}，一眼看懂", "on_screen_text": "新品上市"},
            {"time": "3-8s", "shot": "场景演绎", "voice": "痛点演绎", "on_screen_text": "你是否也遇到"},
            {"time": "8-12s", "shot": "卖点拆解", "voice": "解决方案", "on_screen_text": "核心卖点"},
            {"time": "12-15s", "shot": "促销贴片", "voice": "限时优惠", "on_screen_text": "立即下单"},
        ],
        "tags": ["短视频", "脚本", "规则模板"],
    }


def generate(prompt: str, asset_type: str, style: str) -> dict[str, Any]:
    """生成内容 + 调用元信息。真实文件写入 uploads/ 以便预览与入库。"""
    if asset_type == "copy":
        result = llm.chat_json(
            "generate_copy_v1.md",
            f"素材主题：{prompt}\n投放位置：商品主图详情/信息流\n风格：{style}",
            variables={"style": style}, max_tokens=800, timeout=75.0,
        )
        payload = result.data if result.ok and result.data.get("title") else _rule_copy(prompt, style)
        source = "llm" if (result.ok and result.data.get("title")) else "rule"
        note = "" if source == "llm" else f"规则模板兜底（模型不可用：{result.reason or '输出不合格'}）"
        return {"content_type": "copy", "source": source, "result": payload,
                "meta": _meta(result), "note": note}

    if asset_type == "video":
        result = llm.chat_json(
            "generate_video_script_v1.md",
            f"视频主题：{prompt}\n风格：{style}",
            variables={"style": style}, max_tokens=1200, timeout=75.0,
        )
        payload = result.data if result.ok and result.data.get("scenes") else _rule_script(prompt)
        source = "llm" if (result.ok and result.data.get("scenes")) else "rule"
        note = "" if source == "llm" else f"规则模板兜底（模型不可用：{result.reason or '输出不合格'}）"
        return {"content_type": "video_script", "source": source, "result": payload,
                "meta": _meta(result), "note": note}

    # image：程序化出卡片，不调用模型（避免把「未验证的图像接口」说成已跑通）
    from app.repository import new_asset_id

    asset_id = new_asset_id()
    path = config.UPLOAD_DIR / f"{asset_id}.png"
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dims = render_spec_card(prompt, "image", style, path)
    data_url = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
    return {
        "content_type": "image",
        "source": "programmatic",
        "result": {
            "title": f"{prompt[:20]}｜{dims['width']}×{dims['height']} 投放规格卡",
            "description": f"按 {style} 风格生成的演示图（程序化绘制，非 AI 出图）",
            "tags": [style, "演示图", prompt[:8]],
            "preview_asset_id": asset_id,
        },
        "file": {"path": str(path), "size": path.stat().st_size, "mime_type": "image/png", **dims},
        "preview_data_url": data_url,
        "meta": {"model": "", "endpoint": ""},
        "note": "非真实 AI 出图：Pillow 按投放规格绘制的占位卡片。真实图像模型（wan2.7-image 等）"
                "的调用接口形状尚未在本环境验证，未验证不宣称已跑通。",
    }


def _meta(result: llm.LLMResult) -> dict[str, Any]:
    return {
        "model": result.model,
        "endpoint": result.endpoint,
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "prompt_version": result.prompt_version,
    }
