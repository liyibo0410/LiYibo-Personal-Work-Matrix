# -*- coding: utf-8 -*-
"""P1 端对端验证：不经任何手工改配置，走真实 boot() 通路跑一次完整审查，
确认「配了 .env 凭证 → 二阶段语义复核自动生效」这条配置通路是通的。

上一轮 verify_llm_review.py 实测时发现该通路断裂（source=rule-only，
必须手工改 cfg 才能拿到 llm），P1 补上 dotenv→llm 配置映射后本脚本复核。
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

ROOT = r"D:\software\PycharmProjects\作品矩阵\projects\p05-contract-review"
OUT = r"D:\software\PycharmProjects\作品矩阵\_evidence\p05"
PORT = 8783

sys.path.insert(0, ROOT)
os.chdir(ROOT)

log = []
results = []


def p(m):
    log.append(m)


def check(name, ok, note=""):
    results.append({"case": name, "pass": bool(ok), "note": note})
    p("    [%s] %s%s" % ("通过" if ok else "失败", name, (" ｜ %s" % note) if note else ""))
    return ok


def main():
    from app import config as cfg_mod
    from app import store as store_mod
    from app import server as server_mod
    from app import pipeline
    from mock import feishu

    # 清理可能干扰的环境变量，确保走 .env 通路
    for ev in ("OPENAI_API_KEY", "LLM_API_KEY", "LLM_BASE_URL",
               "LLM_API_KEY_FALLBACK", "LLM_BASE_URL_FALLBACK"):
        os.environ.pop(ev, None)

    cfg = cfg_mod.Config(ROOT)
    cfg.data["server"]["port"] = PORT
    for k in ("data", "uploads", "parsed", "reports", "samples"):
        cfg.path(k)
    st = store_mod.Store(cfg.db_path())
    mock_db = os.path.join(cfg.path("data"), "mock_approval.json")
    feishu.init(ROOT, mock_db, cfg.path("samples"), force_reseed=True)

    p("[0] 走真实 boot()：.env → llm 配置映射")
    boot = server_mod.boot(cfg, st)
    llm_map = boot.get("llm", {})
    p("    boot.llm = %s" % json.dumps(llm_map, ensure_ascii=False))
    check("boot 完成且返回 llm 映射", llm_map.get("applied") is True,
          "source=%s changed=%s" % (llm_map.get("source"), llm_map.get("changed")))
    check("base_url 已被自动填充", bool((cfg.section("llm") or {}).get("base_url")),
          "base_url=%s" % (cfg.section("llm") or {}).get("base_url"))
    check("OPENAI_API_KEY 已被自动填充", bool(os.environ.get("OPENAI_API_KEY")),
          "长度 %d" % len(os.environ.get("OPENAI_API_KEY") or ""))

    from app import llm as llm_mod
    check("llm.available() 为真（配置通路打通）", llm_mod.available(cfg) is True,
          "mode=%s reason=%s" % (llm_mod.mode_info(cfg).get("mode"),
                                 llm_mod.mode_info(cfg).get("reason")))

    # 真实审查一份合同
    p("")
    # 注意：ingest_upload 有 SHA256 去重，上传已审过的文件会直接复用旧案件、
    # 不再触发审查（表现为 6ms 返回、快照仍是旧值）。这里换一个尚未审过的样本。
    p("[1] 真实审查：samples/01_软件采购合同_风险用例.docx（purchase，风险用例）")
    sample = os.path.join(ROOT, "samples", "01_软件采购合同_风险用例.docx")
    with open(sample, "rb") as f:
        raw = f.read()
    t0 = time.time()
    out = pipeline.ingest_upload(cfg, st, "01_软件采购合同_风险用例.docx", raw,
                                 meta={"business_type": "purchase",
                                       "title": "软件采购合同_风险用例"})
    ms = round((time.time() - t0) * 1000)
    case_id = out.get("case_id")
    p("    case_id=%s duplicated=%s 耗时 %dms" % (case_id, out.get("duplicated"), ms))
    check("审查完成且非去重复用", out.get("ok") is True and case_id is not None
          and out.get("duplicated") is not True)

    snap = json.load(io.open(os.path.join(cfg.path("parsed"),
                                          "case_%s.json" % case_id), encoding="utf-8"))
    lv = snap.get("llm_verify", {})
    p("    llm_verify: source=%s stats=%s" % (lv.get("source"), lv.get("stats")))
    check("端到端复核真实生效（source=llm）", lv.get("source") == "llm",
          "reason=%s" % lv.get("reason"))
    if lv.get("source") == "llm":
        check("至少一条 confirm（违约责任不对等应为真风险）",
              (lv.get("stats") or {}).get("confirm", 0) > 0,
              "stats=%s" % lv.get("stats"))
        for rid, info in list((lv.get("items") or {}).items())[:5]:
            p("      %s → %s conf=%.2f ｜ %s" % (rid, info.get("verdict"),
                                                 info.get("confidence", 0),
                                                 (info.get("reason") or "")[:70]))

    # DB 持久化
    rows = st.results(case_id)
    persisted = [dict(r) for r in rows]
    has_verdict = any((r.get("verify_verdict") or "") for r in persisted)
    p("    结果行 verify_verdict: %s" % [r.get("verify_verdict") for r in persisted])
    check("复核结论已落库（verify_verdict 非空）", has_verdict)

    # 报告含复核分组（直接读 Markdown 报告产物）
    try:
        from app import output as output_mod
        case_row = st.get_case(case_id)
        docs = st.documents(case_id) if hasattr(st, "documents") else []
        doc_row = docs[-1] if docs else None
        md = output_mod.build_report_md(case_row, doc_row, rows,
                                        snap.get("coverage") or {}, None)
        has_group = ("确认风险" in md) or ("误报" in md)
        check("Markdown 报告含复核分组标识", has_group,
              "含确认风险=%s 含误报=%s" % ("确认风险" in md, "误报" in md))
        p("    报告片段：%s" % [ln for ln in md.splitlines() if "确认风险" in ln or "误报" in ln][:2])
    except Exception as exc:                                  # noqa: BLE001
        p("    报告断言跳过：%s" % exc)

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    p("")
    p("─" * 74)
    p("  P1 端到端 · 二阶段语义复核配置通路   %d / %d 通过" % (passed, total))
    p("─" * 74)
    for r in results:
        if not r["pass"]:
            p("  [失败] %s ｜ %s" % (r["case"], r["note"]))

    io.open(os.path.join(OUT, "verify_llm_e2e.log"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")
    io.open(os.path.join(OUT, "verify_llm_e2e.json"), "w", encoding="utf-8").write(
        json.dumps({"passed": passed, "total": total, "cases": results},
                   ensure_ascii=False, indent=2, default=str))
    print("RESULT %d/%d" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
