# -*- coding: utf-8 -*-
"""审查引擎 app/review.py 单元测试。

覆盖两条主线：
  1. 纯函数：despace 坐标映射、_cmp 数值比较、_looks_like_regex、classify_clause、
     split_clauses、clause_coverage、extract_metadata、decide_conclusion、build_suggestion；
  2. run_rules 规则引擎：keyword / regex / absence / numeric / asymmetry 五种匹配模式，
     每条命中必须回带原文证据 + 可定位坐标（页码/段落索引/字符区间），
     非法正则必须进 diag 而不是静默失效。
"""
from __future__ import annotations

import pytest

from app import review

from conftest import make_paras


# ------------------------------------------------------------------ despace
def test_despace_removes_cjk_inner_spaces():
    clean, idx = review.despace("合同 金额 为")
    assert clean == "合同金额为"
    # idx_map[i] 是 clean 第 i 字符在原文中的下标，可无损映射回原文
    # 原文：合(0)同(1)_(2)金(3)额(4)_(5)为(6)，两个 CJK 间空格被剔除
    assert idx[0] == 0            # "合"
    assert clean[2] == "金"
    assert idx[2] == 3            # clean 的"金"映射回原文下标 3


def test_despace_keeps_non_cjk_spaces():
    clean, _ = review.despace("USD 100")
    assert clean == "USD 100"     # 非 CJK 之间的空格不动


# ------------------------------------------------------------------ _cmp
@pytest.mark.parametrize("a,op,b,expected", [
    (5, "gt", 3, True), (3, "gt", 5, False),
    (5, "gte", 5, True), (4, "gte", 5, False),
    (2, "lt", 3, True), (3, "lt", 3, False),
    (3, "lte", 3, True), (4, "lte", 3, False),
    (3, "eq", 3, True), (3, "eq", 4, False),
])
def test_cmp(a, op, b, expected):
    assert review._cmp(a, op, b) is expected


def test_cmp_unknown_op_is_false():
    assert review._cmp(1, "nope", 1) is False


# ------------------------------------------------------------------ _looks_like_regex
def test_looks_like_regex():
    assert review._looks_like_regex(r"甲|乙") is True
    assert review._looks_like_regex(r"\d+") is True
    assert review._looks_like_regex("纯关键词") is False


# ------------------------------------------------------------------ classify_clause
def test_classify_clause_hits_keyword_type(clause_types):
    # 违约责任类关键词
    label = review.classify_clause("本合同违约责任如下：逾期交付按日计违约金", clause_types)
    assert label["code"] == "breach"


def test_classify_clause_fallback(clause_types):
    label = review.classify_clause("今天天气不错适合签约", clause_types)
    assert label["code"] == clause_types["fallback"]["code"]


# ------------------------------------------------------------------ split_clauses
def test_split_clauses_attaches_code_and_merges_body(clause_types):
    paras, _ = make_paras([
        "第一条 违约责任",
        "逾期交付的，按合同金额每日万分之五支付违约金。",
        "第二条 争议解决",
        "因本合同引起的争议，双方协商解决。",
    ])
    clauses = review.split_clauses(paras, clause_types)
    # 两个「第X条」标题各起一个条款
    assert len(clauses) == 2
    assert clauses[0]["no"] == "第一条"
    # 正文段并入前一条款
    assert clauses[0]["para_start"] == 0
    assert clauses[0]["para_end"] == 1
    assert "违约金" in clauses[0]["text"]
    # 每段都被打上条款类型标签
    assert paras[1]["clause_code"] == "breach"


def test_clause_coverage_counts_present_and_missing(clause_types):
    paras, _ = make_paras([
        "违约责任：逾期按日计违约金。",
        "争议解决：协商不成提交仲裁。",
    ])
    review.split_clauses(paras, clause_types)     # 会写入 clause_code
    cov = review.clause_coverage(paras, clause_types)
    assert cov["total_types"] == len(clause_types["types"])
    assert 0.0 <= cov["coverage_rate"] <= 1.0
    assert isinstance(cov["present"], list)
    assert isinstance(cov["missing"], list)
    # present + missing 覆盖全部类型
    assert len(cov["present"]) + len(cov["missing"]) == cov["total_types"]


# ------------------------------------------------------------------ extract_metadata
def test_extract_metadata_parties_amount_credit():
    text = (
        "《设备采购合同》\n"
        "甲方：云枢智能科技有限公司\n"
        "乙方：华东机械制造有限公司\n"
        "统一社会信用代码：91310000MA1FL0XX42\n"
        "合同总金额：人民币 120 万元。\n"
    )
    paras, full = make_paras(text.split("\n"))
    meta = review.extract_metadata(paras, full, "设备采购合同.docx")
    assert meta["title"] == "设备采购合同"
    assert "云枢智能" in meta["party_a"]
    assert "华东机械" in meta["party_b"]
    assert meta["credit_code"] == "91310000MA1FL0XX42"
    assert meta["amount"] == 120 * 10000
    assert meta["currency"] == "CNY"


def test_extract_metadata_usd_currency():
    text = "总价：50000 美元。"
    paras, full = make_paras([text])
    meta = review.extract_metadata(paras, full, "x.docx")
    assert meta["currency"] == "USD"
    assert meta["amount"] == 50000


def test_extract_metadata_title_falls_back_to_filename():
    paras, full = make_paras(["正文没有书名号标题。"])
    meta = review.extract_metadata(paras, full, "服务合同.docx")
    assert meta["title"] == "服务合同"


# ------------------------------------------------------------------ decide_conclusion
def test_decide_conclusion_reject_on_high_count():
    th = {"reject_high_count": 2, "rectify_total": 1}
    assert review.decide_conclusion(review.store.R_HIGH, 2, 5, th) == "reject"


def test_decide_conclusion_rectify_on_single_high():
    th = {"reject_high_count": 2, "rectify_total": 1}
    assert review.decide_conclusion(review.store.R_HIGH, 1, 1, th) == "rectify"


def test_decide_conclusion_pass_when_clean():
    th = {"reject_high_count": 2, "rectify_total": 1}
    assert review.decide_conclusion(review.store.R_NONE, 0, 0, th) == "pass"


def test_conclusion_labels_complete():
    assert set(review.CONCLUSION_LABEL) == {"pass", "rectify", "reject"}


# ------------------------------------------------------------------ build_suggestion
def test_build_suggestion_prefers_library(project_root):
    library = review.load_clause_library(project_root)
    # 取库里任一规则 id 验证「优先标准条款库」
    rid = next(iter((library.get("library") or {}).keys()), None)
    if rid is None:
        pytest.skip("条款库为空，跳过库优先分支")
    primary, alts = review.build_suggestion({"rule_id": rid, "suggestion": "内置"}, library)
    assert primary and primary != "内置"
    assert isinstance(alts, list)


def test_build_suggestion_falls_back_to_rule():
    primary, alts = review.build_suggestion(
        {"rule_id": "__not_in_library__", "suggestion": "内置示范条款"}, {})
    assert primary == "内置示范条款"
    assert alts == []


# ------------------------------------------------------------------ run_rules 各模式
def _rule(rid, mode, patterns, **kw):
    base = {"id": rid, "name": rid, "risk_level": "high", "mode": mode,
            "patterns": patterns, "clause_type": "breach", "reason": "r",
            "legal_basis": "", "suggestion_default": "s"}
    base.update(kw)
    return base


def test_run_rules_keyword_mode_anchors_coordinates():
    paras, full = make_paras(["本合同自双方签字盖章之日起生效。", "甲方逾期付款。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("K1", "keyword", ["逾期付款"])]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert len(hits) == 1
    h = hits[0]
    assert h["rule_id"] == "K1"
    assert h["anchored"] is True
    assert "逾期付款" in h["evidence"]
    # 坐标可定位：命中在第 2 段（index=1）
    assert h["para_index"] == 1
    assert h["char_start"] is not None and h["char_end"] is not None


def test_run_rules_absence_mode_hits_when_missing():
    paras, full = make_paras(["正文只约定了交付与付款，未见任何纠纷处理条款。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("A1", "absence", ["争议解决", "仲裁"])]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert len(hits) == 1
    assert hits[0]["rule_id"] == "A1"


def test_run_rules_absence_mode_silent_when_present():
    paras, full = make_paras(["因本合同引起的争议解决方式：提交仲裁委员会仲裁。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("A1", "absence", ["仲裁"])]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert hits == []


def test_run_rules_numeric_mode_threshold():
    paras, full = make_paras(["违约金比例为 30 %。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("N1", "numeric", [r"违约金比例为\s*(\d+)\s*%"],
                             numeric_op="gt", numeric_threshold=20)]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert len(hits) == 1
    assert hits[0]["rule_id"] == "N1"
    assert "实测值 30" in hits[0]["extra"]


def test_run_rules_numeric_mode_below_threshold_no_hit():
    paras, full = make_paras(["违约金比例为 5 %。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("N1", "numeric", [r"违约金比例为\s*(\d+)\s*%"],
                             numeric_op="gt", numeric_threshold=20)]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert hits == []


def test_run_rules_asymmetry_mode_needs_both_sides():
    """门禁用例的引擎级验证：不对等模式必须同时命中「本方不利」与「对方封顶」才成立。"""
    paras, full = make_paras([
        "甲方逾期付款的，按逾期金额每日万分之五计付滞纳金，且赔偿总额不超过合同金额。",
        "乙方违约需承担全部损失，包括间接损失，不设上限。",
    ])
    rule = _rule(
        "SA-H-001", "asymmetry",
        [r"(甲方)[^。；\n]{0,30}(滞纳金|违约金)[^。；\n]{0,20}(万分之)[一二三四五六七八九十0-9]+",
         r"(甲方)[^。；\n]{0,40}(不超过|上限|封顶)"],
        patterns_alt=[r"(乙方)[^。；\n]{0,40}(无上限|不设上限|全部损失|间接损失)"],
    )
    rules = {"contract_type": "sales", "version": "t", "rules": [rule]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert len(hits) == 1
    h = hits[0]
    assert h["rule_id"] == "SA-H-001"
    # 不对等命中必须同时带本方与对方两侧证据
    assert "本方不利" in h["evidence"]
    assert "相对方" in h["evidence"]
    assert h["alt_evidence"]


def test_run_rules_asymmetry_no_hit_when_only_one_side():
    paras, full = make_paras(["乙方违约需承担全部损失，包括间接损失。"])
    rule = _rule("SA-H-001", "asymmetry", [r"甲方[^。；\n]{0,40}封顶"],
                 patterns_alt=[r"乙方[^。；\n]{0,40}全部损失"])
    rules = {"contract_type": "sales", "version": "t", "rules": [rule]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert hits == []          # 缺本方一侧，不成立


def test_run_rules_invalid_regex_goes_to_diag():
    """规则页支持在线编辑，写坏的正则必须被看见（进 diag）而不是静默失效。"""
    paras, full = make_paras(["任意正文。"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("BAD", "regex", [r"(未闭合["])]}
    diag = []
    hits = review.run_rules(full, paras, rules,
                            {"types": [], "fallback": {"code": "general", "label": "通用"}},
                            diag=diag)
    assert hits == []
    assert len(diag) == 1
    assert diag[0]["pattern"] == r"(未闭合["
    assert "BAD" in diag[0]["where"]


def test_run_rules_regex_matches_after_despace():
    """PDF 常见「逐字空格」：去空格后仍能命中，且坐标映射回原文。"""
    paras, full = make_paras(["乙 方 承 担 全 部 损 失"])
    rules = {"contract_type": "sales", "version": "t",
             "rules": [_rule("R1", "regex", [r"乙方承担全部损失"])]}
    hits = review.run_rules(full, paras, rules, {"types": [], "fallback": {"code": "general", "label": "通用"}})
    assert len(hits) == 1
    assert hits[0]["rule_id"] == "R1"
    assert hits[0]["anchored"] is True
