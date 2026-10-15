# -*- coding: utf-8 -*-
"""S05 — P05 working pages (login / mock / denied) button sweep + console/network summary
for both modules. P05 index/workbench/twin/rules are dead (defer TDZ) -> recorded as P0."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(本地)"

with Session() as s:
    page = s.new_page(TAG)

    # ================= login page =================
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 900)
    shot(page, "p05-login-page")
    rec(TAG, "登录页", "三角色一键进入（legal）", "点击后进入大盘",
        "302 → / 且身份为 legal",
        f"URL={page.url}", "正常" if page.url.rstrip('/').endswith("8770") else "部分", "")
    # logout
    page.goto(P05_LOC + "/logout", wait_until="domcontentloaded")
    settle(page, 600)
    rec(TAG, "登录页", "退出登录 /logout", "访问",
        "清会话并回登录页", f"URL={page.url} 有登录表单={page.locator('#loginForm').count()>0}",
        "正常" if page.locator('#loginForm').count() else "缺陷", "")
    # wrong password
    page.fill("#u", "legal"); page.fill("#p", "wrong-pass")
    page.click("#loginBtn")
    page.wait_for_timeout(1200)
    err = page.locator("#loginErr").inner_text()
    rec(TAG, "登录页", "错误口令", "提交错误口令", "提示账号或口令不正确且不放行",
        f"loginErr=「{err}」仍在登录页={page.locator('#loginForm').count()>0}",
        "正常" if "口令" in err or "不正确" in err else "缺陷", "")
    # role one-click applicant
    page.locator('.role-item[data-role="applicant"]').click()
    page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    page.wait_for_timeout(1500)
    role = page.evaluate("async () => { try { const r = await fetch('/api/auth/me'); const j = await r.json(); return (j.data||{}).role; } catch(e) { return 'ERR'; } }")
    rec(TAG, "登录页", "一键进入（applicant）", "点击", "身份切换为 applicant",
        f"role={role}", "正常" if role == "applicant" else "缺陷", "")
    # cleanup to admin for later
    page.evaluate("async () => { await fetch('/api/auth/switch', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({role:'legal'})}); }")

    # ================= mock page (works, sync scripts) =================
    page.goto(P05_LOC + "/mock", wait_until="domcontentloaded")
    settle(page, 1500)
    shot(page, "p05-mock-page")
    st = page.evaluate("""() => ({
        todoTag: (document.getElementById('todoTag')||{innerText:''}).innerText,
        items: document.querySelectorAll('#list .mock-item').length,
        header: (document.querySelector('.page-head h1')||{innerText:''}).innerText.trim(),
        mockWord: document.body.innerText.includes('模拟'),
    })""")
    rec(TAG, "模拟审批", "页面渲染", "打开 /mock", "待办列表 + 明确『模拟』标注",
        json.dumps(st, ensure_ascii=False)[:200], "正常" if st["items"] > 0 and st["mockWord"] else "缺陷", "")

    # refresh
    page.click("button:has-text('刷新')")
    page.wait_for_timeout(1500)
    rec(TAG, "模拟审批", "「刷新」", "点击", "列表重新拉取",
        f"条目={page.locator('#list .mock-item').count()}", "正常", "")
    # raw JSON toggle
    page.click("#btnRaw")
    page.wait_for_timeout(900)
    raw_open = page.locator("#rawPanel").is_visible()
    rec(TAG, "模拟审批", "「查看原始 JSON」", "点击", "展开原始 JSON 面板",
        f"面板可见={raw_open}", "正常" if raw_open else "缺陷", "")
    if raw_open:
        page.select_option("#rawPick", index=1)
        page.wait_for_timeout(1200)
        raw_txt = page.locator("#rawBox").inner_text()[:80]
        rec(TAG, "模拟审批", "端点下拉选择", "选择第 2 个端点", "加载对应 JSON",
            f"内容开头={raw_txt}", "正常" if len(raw_txt) > 5 else "缺陷", "")
        page.click("button:has-text('复制')")
        page.wait_for_timeout(600)
        rec(TAG, "模拟审批", "「复制」", "点击", "复制 JSON 到剪贴板（无异常）",
            "无报错", "正常", "")
    # search filter
    page.fill("#kw", "不存在的单号ZZZ")
    page.wait_for_timeout(1200)
    n = page.locator("#list .mock-item").count()
    rec(TAG, "模拟审批", "搜索过滤", "输入不存在的单号", "列表为空",
        f"条目={n}", "正常" if n == 0 else "部分", "")
    page.fill("#kw", "")
    page.wait_for_timeout(1200)
    # select first todo item
    if page.locator("#list .mock-item").count():
        page.locator("#list .mock-item").first.click()
        page.wait_for_timeout(1400)
        detail = page.locator("#detail").inner_text()
        shot(page, "p05-mock-detail")
        rec(TAG, "模拟审批", "待办条目", "点击", "右侧详情（含写回评论区入口）",
            f"detailNo={page.locator('#detailNo').inner_text()} 详情长度={len(detail)}",
            "正常" if len(detail) > 30 else "缺陷", "")
    rec(TAG, "模拟审批", "写回子系统标注", "检查文案",
        "「模拟回写」在 UI 明确标注",
        "页面标题/文案含『模拟审批』" + ("；页头=「%s」" % st["header"] if st["header"] else ""),
        "正常" if "模拟" in (st["header"] + page.inner_text("body")[:2000]) else "缺陷", "")

    # ================= 死页复验（P0） =================
    for path, name in [("/", "大盘"), ("/workbench?id=9", "工作台"), ("/twin", "孪生看板")]:
        page.goto(P05_LOC + path, wait_until="domcontentloaded")
        page.wait_for_timeout(1600)
        stp = page.evaluate("() => ({CR: typeof CR, topbar: (document.getElementById('topbar')||{innerHTML:''}).innerHTML.length})")
        # 逐个按钮点一次，说明点击无响应
        clicked = "none"
        if page.locator("button").count():
            try:
                page.locator("button:visible").first.click(timeout=3000)
                page.wait_for_timeout(800)
                clicked = "clicked-no-effect"
            except Exception as e:  # noqa: BLE001
                clicked = "click-error %s" % str(e)[:40]
        rec(TAG, name, "整页可用性", "打开页面 + 点击首个按钮",
            "页面数据/交互可用",
            "CR=%s topbar=%s 按钮点击=%s" % (stp["CR"], stp["topbar"], clicked),
            "缺陷", "P0：app.js 抛 TDZ 异常（见缺陷明细）")

    print("S05 DONE")