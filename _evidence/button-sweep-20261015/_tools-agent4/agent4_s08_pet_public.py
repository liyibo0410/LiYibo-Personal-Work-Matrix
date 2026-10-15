# -*- coding: utf-8 -*-
"""S08 — P05 pet assistant on a working page (mock), mock page anchor button,
plus public re-check for P05/P08 and a fresh P0 verification."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(本地)"

with Session() as s:
    page = s.new_page(TAG)
    # login as legal then go to mock (sync scripts page)
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    settle(page, 600)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_timeout(1200)
    page.goto(P05_LOC + "/mock", wait_until="domcontentloaded")
    settle(page, 1200)

    # ---- pet ----
    rec_row = None
    try:
        page.click("#petBtn", timeout=5000)
        page.wait_for_timeout(1200)
        shot(page, "p05-pet-open-on-mock")
        vis = page.locator("#petPanel").is_visible()
        chips = page.locator(".pet-chip").count()
        tour_btn = page.locator("#petTour").count()
        rec(TAG, "助手(宠物)", "打开面板", "点击右下角机器人", "面板打开，含快捷问题与引导入口",
            f"可见={vis} chips={chips} 引导按钮={tour_btn}", "正常" if vis else "缺陷", "")
        if chips:
            c0 = page.locator(".pet-chip").first.inner_text().strip()
            page.locator(".pet-chip").first.click()
            page.wait_for_timeout(6000)
            body = page.locator("#petPanel").inner_text()
            shot(page, "p05-pet-answer")
            rec(TAG, "助手(宠物)", f"快捷提问「{c0[:18]}」", "点击 chip", "返回基于本地规则/模型的回答",
                f"回答长度={len(body)} 尾部={body[-100:].replace(chr(10),' ')}",
                "正常" if len(body) > 120 else "部分", "")
        # tour
        if tour_btn:
            page.click("#petTour")
            page.wait_for_timeout(1500)
            shot(page, "p05-pet-tour")
            coach = page.locator(".pet-coach").count()
            spot = page.locator(".pet-spot").count()
            rec(TAG, "助手(宠物)", "「带我走一遍」引导", "点击引导",
                "页面元素高亮 + 讲解气泡",
                f"讲解气泡={coach} 高亮框={spot}", "正常" if coach or spot else "缺陷", "")
            # stop tour
            page.keyboard.press("Escape")
            page.wait_for_timeout(600)
    except Exception as e:  # noqa: BLE001
        rec(TAG, "助手(宠物)", "打开面板", "点击", "面板打开", f"异常 {e}", "缺陷", "")

    # ---- mock page 写回评论区 anchor ----
    try:
        page.click("button:has-text('写回评论区')", timeout=4000)
        page.wait_for_timeout(1200)
        y = page.evaluate("() => window.scrollY")
        rec(TAG, "模拟审批", "「写回评论区」锚点", "点击", "滚动到评论端点区域",
            f"scrollY={y}", "正常" if y > 0 else "部分", "")
    except Exception as e:  # noqa: BLE001
        rec(TAG, "模拟审批", "「写回评论区」锚点", "点击", "滚动到端点区域", f"异常 {e}", "缺陷", "")

    # ---- public re-check ----
    pub = s.new_page("公网复测")
    for url, name in [(P05_PUB, "P05 公网"), (P08_PUB, "P08 公网")]:
        try:
            r = pub.goto(url, wait_until="domcontentloaded", timeout=20000)
            pub.wait_for_timeout(1500)
            rec("公网复测", name, "打开入口", "状态码与最终 URL",
                f"status={r.status if r else '?'} url={pub.url}", "正常" if (r and r.status == 200) else "缺陷",
                "时点复查，仅供参照")
        except Exception as e:  # noqa: BLE001
            rec("公网复测", name, "打开入口", "可达性", f"异常 {str(e)[:80]}", "缺陷", "")

    # ---- fresh P0 verify (local index) ----
    p2 = s.new_page("P0复验")
    errs = []
    p2.on("pageerror", lambda e: errs.append(str(e)[:90]))
    p2.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    p2.wait_for_timeout(700)
    p2.locator('.role-item[data-role="legal"]').click()
    p2.wait_for_timeout(2500)
    st = p2.evaluate("() => ({url: location.href, CR: typeof CR, stats: document.querySelectorAll('#stats .stat').length})")
    rec("P0复验", "P05 大盘 (本地)", "重新验证 defer/TDZ", "topbar+7卡+表格可用",
        f"{json.dumps(st)} pageerror={errs[:1]}", "缺陷" if st["CR"] == "undefined" else "正常",
        "2026-10-15 复验时刻")
print("S08 DONE")