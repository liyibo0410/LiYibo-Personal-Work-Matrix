"""P07 检索：中文 n-gram 分词 + 同义组归一 + 字段加权打分的可解释匹配。

原实现是 `query.lower().split()` + 子串包含，中文只有「原文字面连写」才命中 ——
实测 `春季护肤品`、`夏天清爽的防晒霜`、`有没有直播用的背景板` 全部 0 命中。
这里改成：CJK 二元组切分 → 同义组归一 → tags/name/description 三字段加权 → IDF 抑制泛词，
并输出 matched_terms 让每一次命中可解释、可评测。

边界：仍是**文本层**检索，不是 CLIP 多模态向量检索（README/接口 `engine` 字段如实标注）。
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_CJK = re.compile(r"[\u4e00-\u9fff]+")
_LATIN = re.compile(r"[a-z0-9]+")

# 电商素材同义组：两侧都归一到组号，`防晒霜` 才能命中打了 `防晒` 标的素材
SYNONYM_GROUPS: list[set[str]] = [
    {"防晒", "防晒霜", "防晒乳", "spf"},
    {"主图", "头图", "主视图", "商品图"},
    {"海报", "banner", "广告图", "促销图"},
    {"双十一", "双11", "1111", "大促", "促销", "活动"},
    {"直播", "直播间", "背景板"},
    {"详情", "详情页", "长图", "详情图"},
    {"文案", "种草", "口播稿"},
    {"短视频", "视频", "video", "片子"},
    {"零食", "美食", "食品"},
    {"家电", "电器"},
    {"口红", "唇釉", "彩妆"},
    {"运动鞋", "跑鞋", "球鞋"},
    {"面膜", "补水面膜"},
    {"洗发水", "护发", "洗发"},
    {"护肤", "护肤品", "保养"},
    {"清爽", "不油腻", "控油"},
    {"保湿", "补水"},
    {"以旧换新", "换新", "回收"},
    {"成分", "配方", "科技"},
]

_FIELD_WEIGHT = {"tags": 3.0, "name": 2.0, "description": 1.0}
_MIN_SCORE = 0.18  # 低于该归一化得分视为「检索不到」，拒答而不是硬凑结果


def _synonym_key(term: str) -> str:
    for i, group in enumerate(SYNONYM_GROUPS):
        if term in group:
            return f"syn{i}"
    return term


def tokenize_pairs(text: str) -> list[tuple[str, str]]:
    """返回 (原词, 归一词) 对 —— 归一词用于匹配，原词用于给人看的命中理由。"""
    lowered = (text or "").lower()
    pairs: list[tuple[str, str]] = []
    for run in _CJK.findall(lowered):
        if len(run) == 1:
            pairs.append((run, _synonym_key(run)))
            continue
        pairs.extend((run[i:i + 2], _synonym_key(run[i:i + 2])) for i in range(len(run) - 1))
        if len(run) <= 4:
            pairs.append((run, _synonym_key(run)))
    pairs.extend((t, _synonym_key(t)) for t in _LATIN.findall(lowered) if len(t) >= 2)
    # 中英混排（双11）与跨脚本词会被上面的正则拆开，这里按同义词表整词补一遍
    pairs.extend((member, _synonym_key(member))
                 for group in SYNONYM_GROUPS
                 for member in group
                 if len(member) >= 2 and member in lowered)
    return pairs


def tokenize(text: str) -> set[str]:
    """CJK 二元组 + 整词（≤4 字）+ 拉丁词，统一走同义组归一。"""
    return {c for _, c in tokenize_pairs(text)}


def _idf(query_terms: set[str], docs: list[dict[str, Any]]) -> dict[str, float]:
    n = max(len(docs), 1)
    df = Counter()
    for doc in docs:
        df.update(doc["_terms"])
    return {t: math.log(1 + n / (1 + df[t])) for t in query_terms}


def _score(doc: dict[str, Any], query_terms: set[str], idf: dict[str, float],
           display: dict[str, str]) -> tuple[float, list[dict[str, Any]]]:
    fields = {name: tokenize(doc.get(name) if name != "tags" else " ".join(doc.get("tags") or []))
              for name in _FIELD_WEIGHT}
    matched: list[dict[str, Any]] = []
    total_weight = sum(idf.get(t, 1.0) for t in query_terms) or 1.0
    earned = 0.0
    for term in sorted(query_terms):
        hit_fields = [f for f, terms in fields.items() if term in terms]
        if not hit_fields:
            continue
        best = max(_FIELD_WEIGHT[f] for f in hit_fields)
        earned += idf.get(term, 1.0) * best / max(_FIELD_WEIGHT.values())
        matched.append({"term": display.get(term, term), "fields": hit_fields})
    return earned / total_weight, matched


def search(assets: list[dict[str, Any]], query: str, top_k: int = 5,
           asset_type: str | None = None) -> dict[str, Any]:
    pairs = tokenize_pairs(query)
    query_terms = {canon for _, canon in pairs}
    surfaces: dict[str, list[str]] = {}
    for surface, canon in pairs:
        bucket = surfaces.setdefault(canon, [])
        if surface not in bucket:
            bucket.append(surface)
    # 同一个同义组可能被多个原词命中（如「直播背景板」→ 直播 + 背景板），一并回显
    display = {c: "/".join(v[:3]) for c, v in surfaces.items()}
    base = {
        "engine": "cn-ngram+synonym+weighted-field（文本检索，非 CLIP 多模态向量）",
        "query": query,
        "query_terms": sorted(display[c] for c in query_terms),
    }
    if not query_terms:
        return {**base, "refused": True, "reason": "查询为空或无法切出有效词，未执行检索",
                "total": 0, "items": []}

    docs = [a for a in assets if not asset_type or a["asset_type"] == asset_type]
    for doc in docs:
        doc["_terms"] = tokenize(" ".join([doc.get("name", ""), " ".join(doc.get("tags") or []),
                                           doc.get("description", "")]))
    idf = _idf(query_terms, docs)

    scored: list[tuple[float, dict[str, Any], list[dict[str, Any]]]] = []
    for doc in docs:
        score, matched = _score(doc, query_terms, idf, display)
        if score > 0:
            scored.append((score, doc, matched))
    scored.sort(key=lambda x: (-x[0], x[1]["asset_id"]))

    best = scored[0][0] if scored else 0.0
    if best < _MIN_SCORE:
        return {**base, "refused": True,
                "reason": f"最高相关度 {best:.3f} 低于阈值 {_MIN_SCORE}，判定为库内无匹配素材（拒答而非返回弱相关结果）",
                "total": 0, "items": [], "threshold": _MIN_SCORE}

    items = []
    for score, doc, matched in scored[:top_k]:
        item = {k: v for k, v in doc.items() if not k.startswith("_")}
        item["relevance_score"] = round(min(score, 1.0), 3)
        item["matched_terms"] = matched
        items.append(item)
    return {**base, "refused": False, "total": len(items), "items": items,
            "candidates": len(scored), "threshold": _MIN_SCORE}
