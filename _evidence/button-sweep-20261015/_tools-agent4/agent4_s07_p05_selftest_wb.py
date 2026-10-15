# -*- coding: utf-8 -*-
"""S07 — P05: selftest LLM lines (full), writeback on a pulled case (has real mock instance),
and confirm the upload-writeback asymmetry."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(接口旁证)"

with Session() as s:
    page = s.new_page(TAG)
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 700)
    page.locator('.role-item[data-role="admin"]').click()
    page.wait_for_timeout(1500)

    # full selftest LLM lines
    st_ = page.evaluate("""async () => {
      const r = await (await fetch('/api/selftest')).json();
      const checks = (r.data && r.data.checks) || [];
      return {passed: r.data && r.data.passed, n: checks.length, failed: checks.filter(c=>!c.passed).map(c=>c.name),
              llm: checks.filter(c => /llm|模型|大模型|复核/i.test(c.name)).map(c => ({name: c.name, passed: c.passed, detail: c.detail}))};
    }""")
    print("selftest passed:", st_["passed"], "n:", st_["n"], "failed:", st_["failed"])
    for c in st_["llm"]:
        print(" -", c["passed"], "|", c["name"], "|", c["detail"])
    rec(TAG, "自检", "自检中的 LLM/复核项", "GET /api/selftest",
        "自检结论与实际运行模式一致",
        json.dumps(st_["llm"], ensure_ascii=False)[:400],
        "缺陷" if any("未配置" in (c["detail"] or "") for c in st_["llm"]) else "正常",
        "运行中 case 显示 verify.source=llm/available=true，与自检『未配置 llm.base_url』矛盾")

    # find a case with a real mock approval instance
    cand = page.evaluate("""async () => {
      const j = await (await fetch('/api/cases')).json();
      const items = (j.data.items||[]).filter(c => c.approval_instance && c.review_status === 'completed');
      return items.map(c => ({id: c.id, no: c.case_no, inst: c.approval_instance, wb: c.writeback_status, title: c.title})).slice(0, 8);
    }""")
    print("candidates:", json.dumps(cand, ensure_ascii=False)[:600])
    rec(TAG, "回写", "候选案件（有审批实例）", "GET /api/cases", "找到可回写的既有案件",
        json.dumps(cand, ensure_ascii=False)[:300], "正常" if cand else "部分", "")

    if cand:
        c0 = cand[0]
        cid = c0["id"]
        dr = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'dry_run'})})).json();
          const d = r.data||{}; return {code: r.code, mode: d.mode, status: d.status, inst: d.instance_id, chars: (d.payload||'').length};
        }""", cid)
        rec(TAG, "回写", f"既有案件 {cid} 预览回写", "POST dry_run", "生成待写入内容",
            json.dumps(dr, ensure_ascii=False)[:220], "正常" if dr.get("code") == 0 else "缺陷", "")
        lv = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
          const d = r.data||{}; return {code: r.code, status: d.status, skipped: d.skipped, cid: d.comment_id, inst: d.instance_id, msg: d.message};
        }""", cid)
        rec(TAG, "回写", f"既有案件 {cid} 写回审批单（live）", "POST live",
            "评论写入模拟审批系统", json.dumps(lv, ensure_ascii=False)[:260],
            "正常" if lv.get("status") == "success" or lv.get("skipped") else "缺陷", "")
        if lv.get("inst"):
            cm = page.evaluate("""async (inst) => {
              const r = await fetch('/mock/feishu/api/instances/' + inst + '/comments');
              const j = await r.json();
              const items = ((j.data||{}).comments)||[];
              return {status: r.status, n: items.length, lasts: items.slice(-2).map(c => ((c.text||'').slice(0,60)))};
            }""", lv["inst"])
            rec(TAG, "回写", "评论区核对", "GET comments", "新评论可见",
                json.dumps(cm, ensure_ascii=False)[:240], "正常" if cm.get("n", 0) >= 1 else "缺陷", "")
        # 幂等
        lv2 = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
          return {code: r.code, skipped: (r.data||{}).skipped, msg: (r.data||{}).message};
        }""", cid)
        rec(TAG, "回写", "重复 live（幂等）", "再次 POST live", "跳过重复写入",
            json.dumps(lv2, ensure_ascii=False)[:220], "正常" if lv2.get("skipped") else "部分", "")

    # double check the upload-writeback asymmetry statement: uploaded case id 2 has failed wb and retry also fails
    r2 = page.evaluate("""async () => {
      const r = await (await fetch('/api/cases/2/retry', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})})).json();
      return r;
    }""")
    rec(TAG, "工作台", "案例2「重新审查」retry", "POST /api/cases/2/retry", "重试解析/审查",
        json.dumps(r2, ensure_ascii=False)[:220], "正常" if r2.get("code") == 0 else "缺陷", "")
print("S07 DONE")