# -*- coding: utf-8 -*-
"""S07b — P05 as LEGAL: writeback dry_run/live on an existing pulled case (FS-AP-06) +
comment verification + retry of the failed uploaded case."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(接口旁证)"

with Session() as s:
    page = s.new_page(TAG)
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 700)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_timeout(1500)

    for cid, inst in [(6, "FS-AP-06"), (5, "FS-AP-05")]:
        dr = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'dry_run'})})).json();
          const d = r.data||{}; return {code: r.code, mode: d.mode, status: d.status, inst: d.instance_id, chars: (d.payload||'').length};
        }""", cid)
        rec(TAG, "回写", f"案件 {cid} 预览回写（legal）", "POST dry_run", "生成待写入内容",
            json.dumps(dr, ensure_ascii=False)[:220], "正常" if dr.get("code") == 0 else "缺陷", "")
        lv = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
          const d = r.data||{}; return {code: r.code, status: d.status, skipped: d.skipped, cid: d.comment_id, inst: d.instance_id, msg: d.message};
        }""", cid)
        rec(TAG, "回写", f"案件 {cid} 写回审批单（live）", "POST live",
            "评论写入模拟审批系统", json.dumps(lv, ensure_ascii=False)[:260],
            "正常" if lv.get("status") == "success" or lv.get("skipped") else "缺陷", "")
        cm = page.evaluate("""async (inst) => {
          const r = await fetch('/mock/feishu/api/instances/' + inst + '/comments');
          const j = await r.json();
          const items = ((j.data||{}).comments)||[];
          return {status: r.status, n: items.length, last: ((items.slice(-1)[0]||{}).text||'').slice(0,100)};
        }""", inst)
        rec(TAG, "回写", f"案件 {cid} 评论区核对", "GET comments", "新评论可见",
            json.dumps(cm, ensure_ascii=False)[:240], "正常" if cm.get("n", 0) >= 1 else "缺陷", "")
        lv2 = page.evaluate("""async (cid) => {
          const r = await (await fetch('/api/cases/' + cid + '/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
          return {code: r.code, skipped: (r.data||{}).skipped};
        }""", cid)
        rec(TAG, "回写", f"案件 {cid} 重复 live（幂等）", "再次 POST live", "跳过重复写入",
            json.dumps(lv2, ensure_ascii=False)[:160], "正常" if lv2.get("skipped") else "部分", "")

    # the uploaded case: writeback + retry (the "重试回写" button path)
    lv3 = page.evaluate("""async () => {
      const r = await (await fetch('/api/cases/2/writeback', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode:'live'})})).json();
      const d = r.data||{}; return {code: r.code, status: d.status, msg: d.message};
    }""")
    rec(TAG, "回写", "案件 2（本地上传）重试回写", "POST live 再试",
        "与首次一致（仍失败）", json.dumps(lv3, ensure_ascii=False)[:220], "缺陷",
        "根因：ensure_instance 仅在 approval.base_url 为空时向模拟系统登记实例；本项目演示配置把 base_url 指向自身 HTTP 模拟端（approval_http），上传合同因此永远没有真实实例")

    # check mock instances list to prove FS-AP-LOCAL-2 absent
    insts = page.evaluate("""async () => {
      const r = await fetch('/mock/feishu/api/todo');
      const j = await r.json();
      return {status: r.status, n: ((j.data||{}).items||[]).length,
              ids: ((j.data||{}).items||[]).map(i=>i.instance_id).slice(0,10)};
    }""")
    rec(TAG, "模拟审批", "已登记审批实例清单", "GET /todo", "本地实例 FS-AP-LOCAL-2 应存在",
        json.dumps(insts, ensure_ascii=False)[:240], "缺陷" if "FS-AP-LOCAL-2" not in (insts.get("ids") or []) else "正常", "")
print("S07b DONE")