# -*- coding: utf-8 -*-
"""S03 — P05: admin login → rules page (defer?) / workbench / denied page evidence."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(本地)"

with Session() as s:
    # ---- legal → /rules = 403 denied page ----
    page = s.ctx.new_page()
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 600)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    page.goto(P05_LOC + "/rules", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    shot(page, "p05-denied-403-legal-rules")
    txt = page.inner_text("body")[:180].replace("\n", " | ")
    rec(TAG, "越权页(403)", "legal 访问 /rules", "直接访问",
        "403 友好拒绝页，而不是白屏或直接放开",
        f"URL={page.url} CR={page.evaluate('typeof CR')} 文本={txt}", "正常", "agent4-denied-403 screenshot")

    # ---- admin → /rules ----
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 600)
    page.locator('.role-item[data-role="admin"]').click()
    page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    page.goto(P05_LOC + "/rules", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    st = page.evaluate("() => ({url: location.href, CR: typeof CR, typeList: (document.getElementById('typeList')||{innerHTML:''}).innerHTML.length})")
    shot(page, "p05-rules-admin-load")
    rec(TAG, "规则库", "admin 访问 /rules", "打开规则页",
        "规则库渲染（类型列表/规则表）",
        json.dumps(st, ensure_ascii=False), "正常" if st["CR"] == "object" and st["typeList"] > 0 else "缺陷", "")

    # if broken, click 新增规则 to show failure
    try:
        page.click("button:has-text('新增规则')", timeout=4000)
        page.wait_for_timeout(900)
        opened = page.locator("#mRule").evaluate("el => el.classList.contains('on')")
        rec(TAG, "规则库", "「新增规则」按钮", "点击", "打开编辑弹窗", f"弹窗打开={opened}",
            "正常" if opened else "缺陷", "")
        if opened:
            page.click("#mRule button:has-text('取消')")
    except Exception as e:  # noqa: BLE001
        rec(TAG, "规则库", "「新增规则」按钮", "点击", "打开编辑弹窗", f"异常 {e}", "缺陷", "")

    # ---- admin → workbench ----
    page.goto(P05_LOC + "/", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    # find a case id from API
    cid = page.evaluate("async () => { try { const r = await fetch('/api/cases'); const j = await r.json(); return (j.data.items[0]||{}).id || 0; } catch(e) { return 0; } }")
    page.goto(P05_LOC + "/workbench?id=" + str(cid), wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    stw = page.evaluate("() => ({CR: typeof CR, body: document.getElementById('doc') ? document.getElementById('doc').innerHTML.length : -1})")
    shot(page, "p05-workbench-admin-load")
    rec(TAG, "工作台", f"admin 打开 /workbench?id={cid}", "打开工作台",
        "合同正文 + 风险清单渲染",
        json.dumps(stw, ensure_ascii=False), "正常" if stw["body"] > 100 else "缺陷", "")

print("S03 DONE")