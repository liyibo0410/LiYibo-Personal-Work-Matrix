# -*- coding: utf-8 -*-
"""S06 — P05 engine probe via API (UI is unreachable due to the P0 defer/TDZ bug).
Creates ONE test case titled 「UI测试-可删」 from a repo sample docx, then walks
review -> dry_run -> live writeback -> report. Seeds untouched."""
import base64
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(接口旁证)"

SAMPLE = WORKSPACE / "projects" / "p05-contract-review" / "samples" / "01_软件采购合同_风险用例.docx"
b64 = base64.b64encode(SAMPLE.read_bytes()).decode("ascii")

with Session() as s:
    page = s.new_page(TAG)

    # login as legal through the real login page (cookie in context)
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 700)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_timeout(1800)
    me = page.evaluate("async () => (await (await fetch('/api/auth/me')).json()).data")
    rec(TAG, "会话", "legal 登录", "一键进入", "role=legal",
        f"role={me.get('role')} caps={len(me.get('caps') or [])}", "正常" if me.get("role") == "legal" else "缺陷", "")

    # 1) invalid file type
    bad = page.evaluate("""async (b64) => {
      const r = await fetch('/api/upload', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({filename:'UI测试-可删.txt', content: btoa('hello'), meta:{title:'UI测试-可删'}, auto_review:true})});
      return {status: r.status, body: await r.json()};
    }""", base64.b64encode(b"hello").decode())
    rec(TAG, "上传", "不支持的类型 .txt", "POST /api/upload",
        "拒绝并给出可读提示", json.dumps(bad, ensure_ascii=False)[:220],
        "正常" if bad["status"] == 400 else "缺陷", "")

    # 2) valid upload (my test case) — legal lacks submit_contract; server should 403
    up = page.evaluate("""async (b64) => {
      const r = await fetch('/api/upload', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({filename:'01_软件采购合同_风险用例.docx', content: b64, meta:{business_type:'purchase', title:'UI测试-可删'}, auto_review:true})});
      return {status: r.status, body: await r.json()};
    }""", b64)
    rec(TAG, "上传", "legal 上传合同（无该能力）", "POST /api/upload",
        "403（服务端拦截，前端显隐只是体验）",
        f"status={up['status']} msg={(up['body'] or {}).get('msg','')}", "正常" if up["status"] == 403 else "缺陷", "")

    # switch to applicant for submit
    page.evaluate("async () => { await fetch('/api/auth/switch', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({role:'applicant'})}); }")
    up2 = page.evaluate("""async (b64) => {
      const r = await fetch('/api/upload', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({filename:'01_软件采购合同_风险用例.docx', content: b64, meta:{business_type:'purchase', title:'UI测试-可删'}, auto_review:true})});
      return {status: r.status, body: await r.json()};
    }""", b64)
    cid = ((up2["body"] or {}).get("data") or {}).get("case_id") or 0
    rec(TAG, "上传", "applicant 上传 docx（标题 UI测试-可删）", "POST /api/upload",
        "创建任务并自动审查", f"status={up2['status']} case_id={cid}",
        "正常" if cid else "缺陷", "")

    # 3) case detail (verify LLM stage + risk results)
    if cid:
        det = page.evaluate("""async (cid) => {
          const d = (await (await fetch('/api/cases/' + cid)).json()).data;
          return {status: d.case.review_status, risk: d.case.risk_level, results: (d.results||[]).length,
                  summary_source: (d.summary||{}).summary_source,
                  mode_compare: d.mode_compare ? {cur: d.mode_compare.current, verify: d.mode_compare.verify} : null,
                  mode_info: d.mode_info, llm_mode: d.mode_compare && d.mode_compare.model};
        }""", cid)
        rec(TAG, "审查结果", f"GET /api/cases/{cid}", "读取审查详情",
            "审查完成 + 命中清单 + 模式信息",
            json.dumps(det, ensure_ascii=False)[:400],
            "正常" if det["status"] == "completed" else "缺陷", "")

    # 4) dry_run writeback
    dr = page.evaluate("""async (cid) => {
      const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'dry_run'})})).json();
      const d = r.data || {};
      return {code: r.code, status: d.status, mode: d.mode, chars: (d.payload||'').length, msg: d.message};
    }""", cid)
    rec(TAG, "回写", "预览回写内容（dry_run）", "POST writeback",
        "生成待写入评论内容、不写入平台",
        json.dumps(dr, ensure_ascii=False)[:240],
        "正常" if dr.get("code") == 0 and dr.get("mode") == "dry_run" else "缺陷", "")

    # 5) live writeback
    lv = page.evaluate("""async (cid) => {
      const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
      const d = r.data || {};
      return {code: r.code, status: d.status, skipped: d.skipped, cid: d.comment_id, inst: d.instance_id, msg: d.message};
    }""", cid)
    rec(TAG, "回写", "写回审批单（live）", "POST writeback",
        "评论写入模拟审批系统并返回 comment_id",
        json.dumps(lv, ensure_ascii=False)[:240],
        "正常" if lv.get("code") == 0 and lv.get("status") == "success" else "缺陷", "")

    # 6) verify the comment landed (mock approval raw endpoint)
    if lv.get("inst"):
        cm = page.evaluate("""async (inst) => {
          const r = await fetch('/mock/feishu/api/instances/' + inst + '/comments');
          return r.status + ' ' + (await r.text()).slice(0, 220);
        }""", lv["inst"])
        rec(TAG, "回写", "核对模拟审批评论区", "GET /mock/feishu/api/instances/{id}/comments",
            "能看到刚写入的审查意见评论", cm[:260], "正常" if "衡鉴" in cm or "审查" in cm else "缺陷", "")

    # 7) idempotency: live again
    lv2 = page.evaluate("""async (cid) => {
      const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
      return {code: r.code, skipped: (r.data||{}).skipped, msg: (r.data||{}).message};
    }""", cid)
    rec(TAG, "回写", "重复 live 回写（幂等）", "POST writeback 再次",
        "跳过重复写入", json.dumps(lv2, ensure_ascii=False)[:200],
        "正常" if lv2.get("code") == 0 and lv2.get("skipped") else "部分", "")

    # 8) reports
    rep_md = page.evaluate("""async (cid) => {
      const r = await fetch('/api/cases/' + cid + '/report?format=md');
      const t = await r.text(); return {status: r.status, len: t.length, head: t.slice(0, 90)};
    }""", cid)
    rec(TAG, "报告", "导出 Markdown", "GET /report?format=md",
        "200 + Markdown 文本", json.dumps(rep_md, ensure_ascii=False)[:200],
        "正常" if rep_md["status"] == 200 and rep_md["len"] > 100 else "缺陷", "")
    rep_pdf = page.evaluate("""async (cid) => {
      const r = await fetch('/api/cases/' + cid + '/report?format=pdf');
      const b = await r.arrayBuffer(); return {status: r.status, bytes: b.byteLength, ctype: r.headers.get('content-type')};
    }""", cid)
    rec(TAG, "报告", "导出 PDF", "GET /report?format=pdf",
        "200 + PDF 字节流", json.dumps(rep_pdf, ensure_ascii=False)[:200],
        "正常" if rep_pdf["status"] == 200 and rep_pdf["bytes"] > 1000 else "缺陷", "")

    # 9) re-review + rerun endpoints
    rv = page.evaluate("""async (cid) => {
      const r = await (await fetch('/api/cases/' + cid + '/review', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})})).json();
      return {code: r.code, hits: (r.data||{}).hits, blocked: (r.data||{}).blocked};
    }""", cid)
    rec(TAG, "审查", "重新审查（review）", "POST /review", "返回命中数",
        json.dumps(rv, ensure_ascii=False)[:160], "正常" if rv.get("code") == 0 else "缺陷", "")

    # 10) admin: selftest (LLM status), metrics, twin, scheduler, queue, rules
    page.evaluate("async () => { await fetch('/api/auth/switch', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({role:'admin'})}); }")
    st_ = page.evaluate("""async () => {
      const r = await (await fetch('/api/selftest')).json();
      const checks = (r.data && r.data.checks) || [];
      return {passed: r.data && r.data.passed, n: checks.length,
              llm: checks.filter(c => /llm|模型|大模型/i.test(c.name)).map(c => ({name: c.name, passed: c.passed, detail: (c.detail||'').slice(0,160)}))};
    }""")
    rec(TAG, "自检", "一键自检（admin）", "GET /api/selftest",
        "返回验收项；LLM 复核状态如实标注",
        json.dumps(st_, ensure_ascii=False)[:420],
        "正常" if st_.get("n", 0) > 0 else "缺陷", "")
    for ep, name in [("/api/metrics", "运行指标"), ("/api/twin", "孪生看板"), ("/api/queue", "队列"), ("/api/scheduler", "调度"), ("/api/rules?type=purchase", "规则库")]:
        r = page.evaluate("""async (ep) => { const r = await fetch(ep); const t = await r.text(); return {s: r.status, len: t.length, head: t.slice(0,120)}; }""", ep)
        rec(TAG, "接口", f"{name} {ep}", "GET", "200 + JSON",
            json.dumps(r, ensure_ascii=False)[:200], "正常" if r["s"] == 200 else "缺陷", "")

    print("S06 DONE; test case id =", cid)