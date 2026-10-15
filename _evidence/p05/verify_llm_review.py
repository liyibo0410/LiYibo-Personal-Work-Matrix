# -*- coding: utf-8 -*-
"""P1 独立验证：LLM 二阶段语义复核（任务卡 2 的验收核心）

Qoder 的 66/66 自检全部在「未配 Key」降级路径下跑 —— LLM 真实调用路径 0 覆盖。
本脚本补上这个关键盲区，并顺带验证：
  1. 缺失的 .env → llm 配置映射是否真的不存在（静态核查疑点）
  2. 配置好 LLM 后端到端跑一份合同，验证复核真的发生
  3. 复核结论写入 DB / 快照 / 报告
  4. 误报降权生效（不影响结论但保留证据）
  5. 未配 Key 回归：审查照常完成
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p05-contract-review"
WORKSPACE = r"D:\software\PycharmProjects\作品矩阵"
OUT = r"D:\software\PycharmProjects\作品矩阵\_evidence\p05"
PORT = 8782

sys.path.insert(0, ROOT)
os.chdir(ROOT)

log = []
results = []


def p(msg):
    log.append(msg)


def check(name, ok, note=""):
    results.append({"case": name, "pass": bool(ok), "note": note})
    p("    [%s] %s %s" % ("通过" if ok else "失败", name, ("｜ %s" % note) if note else ""))
    return ok


def main():
    # ---------- 0. 静态核查：.env 映射逻辑是否存在 ----------
    p("[0] 静态核查：.env → llm 配置映射")
    server_src = io.open(os.path.join(ROOT, "app", "server.py"), encoding="utf-8").read()
    pipeline_src = io.open(os.path.join(ROOT, "app", "pipeline.py"), encoding="utf-8").read()
    llm_src = io.open(os.path.join(ROOT, "app", "llm.py"), encoding="utf-8").read()
    has_mapping = ("LLM_BASE_URL" in server_src or "LLM_BASE_URL" in pipeline_src
                   or "LLM_BASE_URL" in llm_src or "OPENAI_API_KEY" in pipeline_src)
    check("任务卡要求的 .env→llm 配置映射存在", has_mapping,
          "若失败：base_url 留空时 LLM 永远不会被启用，Key 白配了" if not has_mapping else "代码中存在 LLM_BASE_URL/OPENAI_API_KEY 引用")

    # ---------- 1. 未配 Key 回归 ----------
    p("")
    p("[1] 未配 Key 回归（确保复核不破坏原流程）")
    from app import config as cfg_mod
    from app import store as store_mod
    from app import pipeline
    from app import llm as llm_mod
    from mock import feishu

    cfg = cfg_mod.Config(ROOT)
    cfg.data["server"]["port"] = PORT
    for k in ("data", "uploads", "parsed", "reports", "samples"):
        cfg.path(k)
    st = store_mod.Store(cfg.db_path())
    mock_db = os.path.join(cfg.path("data"), "mock_approval.json")
    feishu.init(ROOT, mock_db, cfg.path("samples"), force_reseed=False)

    for ev in ("OPENAI_API_KEY",):
        os.environ.pop(ev, None)
    cfg.data["llm"]["enabled"] = False

    # 用样本 docx 走一遍完整审查
    sample = os.path.join(ROOT, "samples", "03_大额销售合同_违约责任不对等.docx")
    with open(sample, "rb") as f:
        raw = f.read()
    out = pipeline.ingest_upload(cfg, st, "03_大额销售合同_违约责任不对等.docx", raw,
                                 meta={"business_type": "sales", "title": "大额销售合同_违约责任不对等"})
    p("    ingest_upload 返回：ok=%s case_id=%s" % (out.get("ok"), out.get("case_id")))
    case_id = out.get("case_id")
    check("未配 Key 时审查流程正常完成", out.get("ok") is True and case_id is not None)

    # 快照里的复核状态
    snap_path = os.path.join(cfg.path("parsed"), "case_%s.json" % case_id)
    snap = json.load(io.open(snap_path, encoding="utf-8"))
    p("    快照 verify: source=%s reason=%s" %
      (snap.get("llm_verify", {}).get("source"), snap.get("llm_verify", {}).get("reason")))
    check("快照 llm_verify.source == rule-only", snap.get("llm_verify", {}).get("source") == "rule-only")
    check("快照 llm_verify.reason 非空", bool(snap.get("llm_verify", {}).get("reason")))

    # 审计里有 review.llm_verify 条目
    audits = st.audit_list(limit=300)
    audit_str = json.dumps(audits, ensure_ascii=False, default=str)
    check("审计留痕包含 review.llm_verify", "review.llm_verify" in audit_str)

    # 结果表有 verify 字段
    rows = st.results(case_id)
    check("未配 Key 时命中数 > 0（违约责任不对等用例应有命中）", len(rows) > 0,
          "hits=%d" % len(rows))
    if rows:
        r0 = dict(rows[0])
        p("    结果行 verify keys: %s" % sorted([k for k in r0.keys() if "verify" in k.lower()]))
        has_v = any("verify_verdict" in dict(r) for r in rows)
        check("结果表持久化 verify 字段", has_v, "")

    # ---------- 2. 配置 LLM 后的端到端 ----------
    p("")
    p("[2] 配置 LLM 后端到端（Token Plan 通道，qwen3.8-flash）")
    # 模拟已正确配置：用 fallback 通道（Token Plan，sk-sp-）
    fb_key = os.environ.get("LLM_API_KEY_FALLBACK", "")
    if not fb_key:
        # 从工作区 .env 读
        envf = os.path.join(WORKSPACE, ".env")
        if os.path.isfile(envf):
            for line in io.open(envf, encoding="utf-8"):
                line = line.strip()
                if line.startswith("LLM_API_KEY_FALLBACK="):
                    fb_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    check("Token Plan Key 可读取", bool(fb_key), "长度 %d" % len(fb_key))

    if fb_key:
        # 造一个小 Case 直接调 review_hits（不走完整管线，控制变量）
        # 用 mock 待办里的一份合同内容
        cases = st.list_cases()
        case = None
        for c in cases:
            if c.get("id") == case_id:
                case = c
                break
        if case is None and cases:
            case = cases[0]

        # 重新解析一份已有 case 的文本作为输入
        snap2 = snap  # 用上面那份
        paras = snap2.get("paragraphs", [])
        text_full = "".join(pp.get("text", "") for pp in paras)
        # 取该 case 的结果作为 hits
        hits_rows = st.results(case_id)
        hits = []
        for r in hits_rows:
            if isinstance(r, dict):
                hits.append({
                    "rule_id": r.get("rule_id"), "rule_name": r.get("rule_name"),
                    "risk_level": r.get("risk_level"), "clause_type": r.get("clause_type"),
                    "evidence": r.get("evidence"), "reason": r.get("reason"),
                    "char_start": r.get("char_start") or 0, "char_end": r.get("char_end") or 0,
                })

        cfg_v = cfg_mod.Config(ROOT)
        cfg_v.data["llm"]["enabled"] = True
        cfg_v.data["llm"]["base_url"] = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        cfg_v.data["llm"]["model"] = "qwen3.8-flash"
        cfg_v.data["llm"]["api_key_env"] = "OPENAI_API_KEY"
        os.environ["OPENAI_API_KEY"] = fb_key

        t0 = time.time()
        vr = llm_mod.review_hits(cfg_v, case or {"title": "测试", "business_type": "sales"}, hits, text_full, paras)
        ms = round((time.time() - t0) * 1000)
        p("    review_hits 返回 source=%s reason=%s stats=%s 耗时 %dms" %
          (vr.get("source"), vr.get("reason"), vr.get("stats"), ms))
        check("LLM 真实调用成功（source=llm）", vr.get("source") == "llm",
              "reason=%s" % vr.get("reason"))
        if vr.get("source") == "llm":
            stats = vr.get("stats", {})
            check("复核 stats 字段完整", set(stats) >= {"confirm", "false_positive", "need_human", "total"},
                  "stats=%s" % stats)
            # 每条命中都有复核结论
            covered = sum(1 for h in hits if h.get("rule_id") in vr.get("items", {}))
            check("所有命中都有复核结论", covered == len(hits),
                  "覆盖 %d/%d" % (covered, len(hits)))
            # 至少一条 confirm（这份合同的违约责任不对等是真风险）
            any_confirm = stats.get("confirm", 0) > 0
            check("违约责任不对等用例至少一条 confirm", any_confirm,
                  "confirm=%s" % stats.get("confirm"))
            # 展示一条示例
            items = vr.get("items", {})
            for rid, info in list(items.items())[:3]:
                p("      %s → %s (conf=%.2f) %s" % (rid, info.get("verdict"), info.get("confidence", 0),
                                                    (info.get("reason") or "")[:60]))

        # 健壮性：LLM 返回非法 JSON
        p("    [健壮性] 模拟 LLM 返回非法 JSON")
        orig_chat = llm_mod.chat
        def fake_chat(cfg_x, s, u):
            return "这不是 JSON，全是废话 ###", ""
        llm_mod.chat = fake_chat
        try:
            vr_bad = llm_mod.review_hits(cfg_v, case or {"title": "t"}, hits, text_full, paras)
            check("非法 JSON → 整体降级 rule-only", vr_bad.get("source") == "rule-only",
                  "reason=%s" % vr_bad.get("reason"))
        finally:
            llm_mod.chat = orig_chat

        # 健壮性：LLM 返回 markdown 围栏 JSON
        p("    [健壮性] 模拟返回 ```json 围栏")
        def fake_chat2(cfg_x, s, u):
            good = json.dumps([
                {"序号": i + 1, "verdict": "confirm", "confidence": 0.9, "reason": "围栏测试"}
                for i in range(len(hits))], ensure_ascii=False)
            return "```json\n%s\n```" % good, ""
        llm_mod.chat = fake_chat2
        try:
            vr_fence = llm_mod.review_hits(cfg_v, case or {"title": "t"}, hits, text_full, paras)
            check("```json 围栏 → 正确解析 source=llm", vr_fence.get("source") == "llm",
                  "stats=%s" % vr_fence.get("stats"))
        finally:
            llm_mod.chat = orig_chat

        # 健壮性：低置信度 false_positive 转 need_human
        p("    [健壮性] 低置信度 false_positive 处理")
        def fake_chat3(cfg_x, s, u):
            good = json.dumps([
                {"序号": i + 1, "verdict": "false_positive", "confidence": 0.3, "reason": "低置信误报"}
                for i in range(len(hits))], ensure_csv=False, ensure_ascii=False) if False else json.dumps([
                {"序号": i + 1, "verdict": "false_positive", "confidence": 0.3, "##reason": ""}
                for i in range(len(hits))], ensure_ascii=False)
            return good, ""
        llm_mod.chat = fake_chat3
        try:
            vr_low = llm_mod.review_hits(cfg_v, case or {"title": "t"}, hits, text_full, paras)
            items_low = vr_low.get("items", {})
            n_human = sum(1 for v in items_low.values() if v.get("verdict") == "need_human")
            check("低置信度 false_positive → need_human", n_human > 0,
                  "need_human=%d" % n_human)
        finally:
            llm_mod.chat = orig_chat

        os.environ.pop("OPENAI_API_KEY", None)

    # ---------- 汇总 ----------
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    p("")
    p("─" * 74)
    p("  P1 独立验证 · LLM 二阶段语义复核   %d / %d 通过" % (passed, total))
    p("─" * 74)
    for r in results:
        if not r["pass"]:
            p("  [失败] %s ｜ %s" % (r["case"], r["note"]))

    io.open(os.path.join(OUT, "verify_llm_review.log"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")
    io.open(os.path.join(OUT, "verify_llm_review.json"), "w", encoding="utf-8").write(
        json.dumps({"passed": passed, "total": total, "cases": results},
                   ensure_ascii=False, indent=2, default=str))
    print("RESULT %d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
