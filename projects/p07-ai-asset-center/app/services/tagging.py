"""P07 智能打标：优先真调 LLM，凭证不可用时退回词表规则，并在返回值里标明来源。

`source` 只有 `llm` / `rule` 两种，前端与评测都按它区分展示 —— 不允许把规则兜底
包装成「AI 打标」。
"""
from __future__ import annotations

from typing import Any

from app.services import llm

# 规则兜底词表：命中名称/描述里的关键词即产标签（非模型产出，source=rule）
_LEXICON: dict[str, dict[str, tuple[str, ...]]] = {
    "品类": {
        "防晒": ("防晒", "spf", "防晒霜"),
        "面膜": ("面膜",),
        "口红": ("口红", "唇釉", "彩妆"),
        "洗发水": ("洗发水", "洗发", "护发"),
        "运动鞋": ("运动鞋", "跑鞋", "球鞋"),
        "零食": ("零食", "礼包", "美食"),
        "家电": ("家电", "电器"),
        "护肤": ("护肤", "保养", "水乳"),
    },
    "场景": {
        "主图": ("主图", "头图"),
        "详情页": ("详情页", "详情"),
        "Banner": ("banner", "广告图"),
        "海报": ("海报",),
        "直播间": ("直播", "背景板"),
        "短视频": ("短视频", "视频", "片子"),
        "脚本": ("脚本",),
        "文案": ("文案", "口播"),
        "科普": ("科普", "成分", "解析"),
        "对比": ("对比",),
    },
    "节点": {
        "春季": ("春季", "春天"),
        "夏季": ("夏季", "夏天"),
        "618": ("618",),
        "双11": ("双11", "双十一"),
        "以旧换新": ("以旧换新", "换新"),
    },
    "风格": {
        "清爽": ("清爽", "控油", "不油腻"),
        "保湿": ("保湿", "补水"),
        "科技感": ("科技",),
        "种草": ("种草",),
        "情感": ("情感", "故事"),
    },
}

_MAX_TAGS = 10


def rule_tags(text: str) -> list[str]:
    lowered = (text or "").lower()
    tags: list[str] = []
    for group in _LEXICON.values():
        for label, needles in group.items():
            if any(n.lower() in lowered for n in needles) and label not in tags:
                tags.append(label)
    return tags[:_MAX_TAGS]


def _validate_llm_tags(parsed: dict[str, Any]) -> list[str]:
    raw = parsed.get("tags")
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        tag = str(item).strip().replace("，", ",")
        if not tag or len(tag) > 12 or "," in tag or tag.isdigit():
            continue
        if tag not in cleaned:
            cleaned.append(tag)
    return cleaned[:_MAX_TAGS]


def tag_asset(name: str, description: str, asset_type: str = "image") -> dict[str, Any]:
    """产出一组标签 + 来源与调用元信息。LLM 不可用或输出不合格 → 规则兜底并标注。"""
    text = f"{name} {description}".strip()
    result = llm.chat_json(
        "tag_asset_v1.md",
        f"素材名称：{name}\n素材描述：{description or '（无）'}\n素材类型：{asset_type}",
        prefer_fast=True, max_tokens=700, timeout=25.0,
    )
    fallback = rule_tags(text)

    if result.ok:
        tags = _validate_llm_tags(result.data)
        if tags:
            extra = {k: result.data.get(k) for k in ("category", "season") if result.data.get(k)}
            return {"tags": tags, "tag_source": "llm", "meta": _meta(result), **extra}
        reason = "模型返回的 tags 不合格（空/超长/含逗号），已改用词表规则打标"
    else:
        reason = f"模型不可用（{result.reason}），已改用词表规则打标"

    return {
        "tags": fallback or rule_tags(name),
        "tag_source": "rule",
        "meta": _meta(result),
        "degraded_reason": reason,
    }


def _meta(result: llm.LLMResult) -> dict[str, Any]:
    return {
        "source": result.source,
        "model": result.model,
        "endpoint": result.endpoint,
        "prompt_version": result.prompt_version,
        "latency_ms": result.latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "reason": result.reason,
    }
