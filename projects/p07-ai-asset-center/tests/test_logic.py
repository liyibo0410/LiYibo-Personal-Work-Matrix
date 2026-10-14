"""纯逻辑单测：标签规范化、中文分词与同义归一、规则打标词表、文件头嗅探。"""
from __future__ import annotations

import pytest

from app.repository import normalize_tags
from app.services import media, tagging
from app.services.search import search, tokenize, tokenize_pairs


# ── 标签规范化 ──

@pytest.mark.parametrize("raw,expected", [
    ('["a","b"]', ["a", "b"]),
    ("护肤,夏季", ["护肤", "夏季"]),
    ("护肤，夏季、 主图 ", ["护肤", "夏季、 主图"]),   # 中文顿号不是分隔符，保留原样
    ("单标签", ["单标签"]),
    ("", []),
    (None, []),
    ([" 带空格 ", "x"], ["带空格", "x"]),
    ('{"bad": 1}', ['{"bad": 1}']),
])
def test_normalize_tags(raw, expected):
    assert normalize_tags(raw) == expected


# ── 分词与同义归一 ──

def test_tokenize_cjk_bigrams_and_latin():
    surfaces = {s for s, _ in tokenize_pairs("运动鞋 详情页")}
    assert {"运动鞋", "动鞋", "运动", "详情页", "详情", "情页"} <= surfaces
    assert {s for s, _ in tokenize_pairs("618大促")} >= {"618", "大促"}


def test_synonym_group_maps_equivalent_words():
    # 「防晒霜」比「防晒」多出 bigram「晒霜」，但两者都归一到同一同义组 → 检索可互相命中
    assert tokenize("防晒") < tokenize("防晒霜")
    assert "syn0" in tokenize("防晒") and "syn0" in tokenize("防晒霜")
    # 中英混排的「双11」与中文「双十一」经整词补召回后落到同一组
    assert "syn3" in tokenize("双11") and "syn3" in tokenize("双十一")
    assert tokenize_pairs("直播")[0][0] == "直播"


def test_single_char_and_empty_input():
    assert tokenize("图") == {"图"}
    assert tokenize("   ") == set()
    assert tokenize_pairs("") == []


# ── 检索打分与拒答 ──

ASSETS = [
    {"asset_id": "A1", "name": "春季护肤主图", "asset_type": "image", "tags": ["护肤", "主图"], "description": "主推护肤品"},
    {"asset_id": "A2", "name": "直播间背景板", "asset_type": "image", "tags": ["直播", "背景板"], "description": "品牌直播间"},
]


def test_search_scores_are_sorted_and_normalised():
    r = search(ASSETS, "护肤主图")
    assert r["refused"] is False and r["items"][0]["asset_id"] == "A1"
    assert r["items"][0]["relevance_score"] <= 1.0
    scores = [i["relevance_score"] for i in r["items"]]
    assert scores == sorted(scores, reverse=True)


def test_search_refuses_irrelevant_query():
    r = search(ASSETS, "完全无关的航空发动机")
    assert r["refused"] is True and r["total"] == 0


def test_search_type_filter_excludes():
    r = search(ASSETS, "直播背景板", asset_type="copy")
    assert r["refused"] is True


# ── 规则打标词表 ──

def test_rule_tags_from_lexicon():
    tags = tagging.rule_tags("夏季防晒霜主图，清爽控油")
    assert "防晒" in tags and "主图" in tags and "清爽" in tags


def test_rule_tags_empty_text():
    assert tagging.rule_tags("") == []


def test_llm_tag_validation_drops_bad_items():
    assert tagging._validate_llm_tags({"tags": ["好标签", "含,逗号", "过长的标签" * 5, 12, ""]}) == ["好标签"]


# ── 文件头嗅探 ──

@pytest.mark.parametrize("head,expected", [
    (b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png"),
    (b"\xff\xd8\xff" + b"0" * 20, "image/jpeg"),
    (b"RIFF" + b"0" * 4 + b"WEBP" + b"0" * 8, "image/webp"),
    (b"GIF89a" + b"0" * 20, "image/gif"),
    (b"\x1a\x45\xdf\xa3" + b"0" * 20, "video/webm"),
    (b"0" * 4 + b"ftyp" + b"isom" + b"0" * 8, "video/mp4"),
    (b"0" * 4 + b"ftyp" + b"qt  " + b"0" * 8, "video/quicktime"),
    (b"MZ\x90\x00" + b"0" * 20, ""),
])
def test_sniff(head, expected):
    assert media._sniff(head) == expected
