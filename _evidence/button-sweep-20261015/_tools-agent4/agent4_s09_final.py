# -*- coding: utf-8 -*-
"""S09 — final re-verify: P05 P0 state + public reachability, right before hand-off."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *
from datetime import datetime

TAG = "P05(收尾复验)"
print("now:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

with Session() as s:
    page = s.new_page(TAG)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:80]))
    page.goto(P05_LOC + "/login", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_timeout(2500)
    st = page.evaluate("() => ({CR: typeof CR, stats: document.querySelectorAll('#stats .stat').length, topbar: (document.getElementById('topbar')||{innerHTML:''}).innerHTML.length})")
    print("P05 index:", st, "errs:", errs[:1])
    rec(TAG, "P05 大盘", "P0 是否仍存在", "登录后检查 CR/统计卡",
        "CR=object 且 7 张卡",
        f"{st} pageerror={errs[:1]}",
        "缺陷" if st["CR"] == "undefined" else "正常", "报告完成时的最终复核")

    # public probe
    p2 = s.ctx.new_page()
    for url in [P05_PUB + "login", P08_PUB]:
        try:
            r = p2.goto(url, wait_until="domcontentloaded", timeout=15000)
            print("public", url, "->", r.status if r else "?")
        except Exception as e:  # noqa: BLE001
            print("public", url, "-> ERR", str(e)[:60])
print("S09 DONE")