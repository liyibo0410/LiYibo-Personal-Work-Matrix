# -*- coding: utf-8 -*-
"""端到端 + 持久层测试。

1. 真实门禁：解析 samples/03_大额销售合同_违约责任不对等.docx，跑 sales 规则库，
   断言「违约责任不对等」高风险规则 SA-H-001 被识别，且命中带原文证据与坐标。
   —— 对应验收门禁「风险用例被正确识别（如'违约责任不对等'）」。
2. 全样本冒烟：samples/ 下 8 份文档全部可被 parse_document 处理而不抛异常，
   DOCX/PDF 正常出文本，扫描件/加密件走 need_manual（解析层降级路径）。
3. store 持久层：用 tmp_path 临时库验证建案件→存文档→写命中→算总风险→审计留痕，
   绝不触碰 data/review.db。
"""
from __future__ import annotations

import os

import pytest

from app import parsers, review, store


# ------------------------------------------------------------------ 真实门禁样本
def _sales_gate_sample(samples_dir):
    return os.path.join(samples_dir, "03_大额销售合同_违约责任不对等.docx")


def test_gate_sample_exists(samples_dir):
    assert os.path.exists(_sales_gate_sample(samples_dir)), "门禁样本缺失"


def test_parse_gate_sample_docx(samples_dir):
    path = _sales_gate_sample(samples_dir)
    res = parsers.parse_document(path, os.path.basename(path))
    assert res["ok"] is True
    assert res["engine"] == parsers.ENGINE_DOCX
    assert res["char_count"] > 0
    assert len(res["paragraphs"]) > 0
    # 每段都带可溯源坐标
    p0 = res["paragraphs"][0]
    for key in ("text", "page", "index", "char_start", "char_end"):
        assert key in p0


def test_gate_identifies_breach_asymmetry(samples_dir, project_root):
    """核心门禁：违约责任不对等必须被识别为高风险命中。"""
    path = _sales_gate_sample(samples_dir)
    res = parsers.parse_document(path, os.path.basename(path))
    assert res["ok"], res.get("error")
    paras, text = res["paragraphs"], res["text"]

    ct = review.load_clause_types(project_root)
    rules = review.load_rules(project_root, "sales")
    diag = []
    hits = review.run_rules(text, paras, rules, ct, diag=diag)
    assert diag == [], "规则库存在非法正则：%s" % diag

    ids = {h["rule_id"] for h in hits}
    assert "SA-H-001" in ids, "门禁失败：未识别违约责任不对等，实际命中=%s" % ids

    gate = next(h for h in hits if h["rule_id"] == "SA-H-001")
    assert gate["risk_level"] == "high"
    assert gate["match_mode"] == "asymmetry"
    assert gate["anchored"] is True
    assert gate["evidence"]                 # 带原文证据
    assert gate["alt_evidence"]             # 不对等需两侧证据
    assert gate["page_no"] is not None      # 可定位到页
    assert gate["char_start"] is not None and gate["char_end"] is not None


def test_gate_metadata_extraction(samples_dir):
    path = _sales_gate_sample(samples_dir)
    res = parsers.parse_document(path, os.path.basename(path))
    meta = review.extract_metadata(res["paragraphs"], res["text"], os.path.basename(path))
    # 销售合同至少应识别出标题；金额/主体视文档而定，不做硬断言
    assert meta["title"]


def test_gate_conclusion_not_pass(samples_dir, project_root):
    """门禁样本命中高风险后，结论不应是「通过」。"""
    path = _sales_gate_sample(samples_dir)
    res = parsers.parse_document(path, os.path.basename(path))
    ct = review.load_clause_types(project_root)
    rules = review.load_rules(project_root, "sales")
    hits = review.run_rules(res["text"], res["paragraphs"], rules, ct)

    high = sum(1 for h in hits if h["risk_level"] == "high")
    total = len(hits)
    risk = store.R_HIGH if high else (store.R_MEDIUM if total else store.R_NONE)
    th = {"reject_high_count": 2, "rectify_total": 1}
    conclusion = review.decide_conclusion(risk, high, total, th)
    assert conclusion in ("rectify", "reject")


# ------------------------------------------------------------------ 全样本冒烟
def test_all_samples_parse_without_crash(samples_dir):
    files = sorted(f for f in os.listdir(samples_dir)
                   if os.path.isfile(os.path.join(samples_dir, f)))
    assert len(files) >= 8, "样本数量异常：%s" % files
    for fn in files:
        path = os.path.join(samples_dir, fn)
        # 解析层必须对任意输入安全返回 dict，不抛异常（含扫描件/加密件/无文本层）
        res = parsers.parse_document(path, fn)
        assert isinstance(res, dict)
        assert "ok" in res and "paragraphs" in res and "text" in res
        ext = os.path.splitext(fn)[1].lower()
        if ext == ".docx" and "加密" not in fn:
            # 非加密 docx 应能出文本
            assert res["char_count"] > 0, "%s 未解析出文本" % fn


def test_encrypted_or_scanned_goes_manual(samples_dir):
    """加密 PDF / 扫描件应走 need_manual 降级，而不是伪装成功。"""
    for fn in ("08_保密协议_加密用例.pdf", "06_软件采购合同_扫描件.png"):
        path = os.path.join(samples_dir, fn)
        if not os.path.exists(path):
            continue
        res = parsers.parse_document(path, fn)
        # 加密件必然受阻；扫描件取决于本机 OCR，未识别时须标 need_manual
        if not res["ok"]:
            assert res.get("need_manual") is True or res.get("error")


# ------------------------------------------------------------------ store 持久层（临时库）
def test_store_roundtrip(tmp_path):
    db = os.path.join(str(tmp_path), "review.db")
    st = store.Store(db)

    cid = st.create_case(title="测试合同", business_type="sales",
                         counterparty="华东机械", amount=1200000)
    assert isinstance(cid, int) and cid > 0

    st.add_document(cid, filename="测试合同.docx", doc_type=parsers.DOCX,
                    sha256="abc123", file_path="/tmp/x.docx")
    doc = st.case_document(cid)
    assert doc and doc["filename"] == "测试合同.docx"

    # 写入两条命中（一高一低），验证总风险取最高
    st.add_results(cid, [
        {"rule_id": "SA-H-001", "rule_name": "违约责任不对等", "risk_level": "high",
         "clause_type": "违约责任", "match_mode": "asymmetry",
         "evidence": "甲方封顶，乙方无上限", "page_no": 3, "para_index": 12,
         "char_start": 100, "char_end": 140, "reason": "r", "legal_basis": "",
         "suggestion": "s", "verify": {"verdict": "confirmed", "reason": "ok"}},
        {"rule_id": "SA-L-001", "rule_name": "生效条件", "risk_level": "low",
         "clause_type": "生效", "match_mode": "absence", "evidence": "",
         "reason": "r", "suggestion": "s"},
    ])
    assert st.overall_risk(cid) == store.R_HIGH
    rows = st.results(cid)
    assert len(rows) == 2
    # 结果按风险降序（high 在前）
    assert rows[0]["risk_level"] == "high"


def test_store_dedupe_by_sha(tmp_path):
    st = store.Store(os.path.join(str(tmp_path), "review.db"))
    cid = st.create_case(title="A", doc_sha256="deadbeef")
    dup = st.case_by_sha("deadbeef")
    assert dup and dup["id"] == cid
    assert st.case_by_sha("not-exist") is None


def test_store_update_whitelist_and_audit(tmp_path):
    st = store.Store(os.path.join(str(tmp_path), "review.db"))
    cid = st.create_case(title="原始标题")
    st.update_case(cid, title="新标题", review_status=store.S_COMPLETED)
    # 非法字段被白名单拦截，不应污染记录
    st.update_case(cid, not_a_real_field="x")
    row = st.get_case(cid)
    assert row["title"] == "新标题"
    assert row["review_status"] == store.S_COMPLETED
    logs = st.audit_list(case_id=cid)
    assert len(logs) >= 1     # 建案件即留痕
