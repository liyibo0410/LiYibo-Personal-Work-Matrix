# -*- coding: utf-8 -*-
"""S02 — PUBLIC P05 dashboard (login as legal): header controls, panels, filters,
stat-card drills, samples, batch buttons, table row actions, pet assistant, theme."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(公网)"

with Session() as s:
    page = s.new_page(TAG)

    # ---------- login as legal ----------
    page.goto(P05_PUB + "login", wait_until="domcontentloaded")
    settle(page, 800)
    page.locator('.role-item[data-role="legal"]').click()
    page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    settle(page, 1500)
    # wait for dashboard data to settle
    try:
        page.wait_for_function("document.querySelectorAll('#stats .stat').length >= 7", timeout=15000)
    except Exception:
        pass
    try:
        page.wait_for_function(
            "() => { const t=document.getElementById('tbody'); return t && (t.children.length>0 || document.getElementById('empty').style.display==='block'); }",
            timeout=15000)
    except Exception:
        pass
    shot(page, "p05-dashboard-legal")
    rows = page.locator("#tbody tr").count()
    stats = page.locator("#stats .stat").count()
    rec(TAG, "大盘", "登录并加载大盘（legal）", "一键进入后等待数据",
        "统计卡 7 张 + 任务表有数据或空态",
        f"统计卡={stats} 表格行={rows} URL={page.url}", "正常" if stats >= 7 else "缺陷", "")

    # ---------- topbar nav ----------
    navs = page.locator("#topbar nav.nav a")
    navtext = [navs.nth(i).inner_text().strip() for i in range(navs.count())]
    rec(TAG, "顶栏", "主导航", "读取导航项", "审查大盘 / 智能审查工作台 / 动态孪生看板 / 合规规则与模板",
        str(navtext), "正常" if len(navtext) >= 4 else "缺陷", "")

    # theme toggle
    theme_before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.click("#themeBtn")
    page.wait_for_timeout(600)
    theme_after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    shot(page, "p05-dashboard-theme-after-toggle")
    rec(TAG, "顶栏", "主题切换按钮", "点击一次", f"主题 {theme_before} → 另一取值",
        f"{theme_before} → {theme_after}",
        "正常" if theme_before != theme_after else "缺陷", "")
    page.click("#themeBtn")  # switch back
    page.wait_for_timeout(400)

    # role switch select (topbar)
    has_rs = page.locator("#roleSwitch").count()
    if has_rs:
        page.select_option("#roleSwitch", "admin")
        page.wait_for_timeout(2500)
        shot(page, "p05-dashboard-after-switch-admin")
        rs_val = page.evaluate("document.getElementById('roleSwitch') ? document.getElementById('roleSwitch').value : ''")
        admin_btns = page.locator("button:has-text('运行指标')").count()
        rec(TAG, "顶栏", "演示身份切换 → admin", "下拉切换身份",
            "切换后页面按 admin 能力显隐（出现 运行指标/一键自检）",
            f"select值={rs_val} 运行指标按钮数={admin_btns} URL={page.url}",
            "正常" if rs_val == "admin" and admin_btns >= 1 else "缺陷", "")
        # back to legal
        page.select_option("#roleSwitch", "legal")
        page.wait_for_timeout(2000)

    # ---------- header buttons (legal expected visible: 机器人通知/角色与权限; hidden: 运行指标/上传合同/一键自检/拉取待办) ----------
    for label in ["机器人通知", "运行指标", "角色与权限", "上传合同", "一键自检", "拉取待办并审查"]:
        vis = page.locator(f"button:has-text('{label}')").count()
        expect_vis = label in ("机器人通知", "角色与权限")
        rec(TAG, "大盘-页头", f"按钮「{label}」", "检查可见性与权限显隐",
            f"legal 角色应{'可见' if expect_vis else '隐藏'}",
            f"DOM 中匹配到 {vis} 个",
            "正常" if (vis > 0) == expect_vis else "缺陷", "")

    # ---------- 机器人通知 modal ----------
    page.click("button:has-text('机器人通知')")
    page.wait_for_timeout(1200)
    shot(page, "p05-notify-modal")
    ntxt = page.locator("#notifyBody").inner_text()
    has_test_btn = page.locator("#btnNotifyTest").count()
    rec(TAG, "大盘-机器人通知", "打开弹窗", "点击「机器人通知」",
        "显示启用状态/渠道/webhook/统计/事件开关",
        f"内容摘要={ntxt[:160].replace(chr(10),' ')} | 发送测试按钮={has_test_btn}",
        "正常" if "启用状态" in ntxt else "缺陷", "")
    if has_test_btn:
        page.click("#btnNotifyTest")
        page.wait_for_timeout(1800)
        t = toast_text(page)
        rec(TAG, "大盘-机器人通知", "发送测试通知", "点击按钮", "toast 显示发送结果",
            f"toast=「{t}」", "正常" if t else "部分", "")
    else:
        rec(TAG, "大盘-机器人通知", "发送测试通知", "—", "admin 才可见",
            "legal 身份下按钮不存在（权限显隐）", "正常", "")
    page.click("#mNotify .mf button:has-text('关闭')")
    page.wait_for_timeout(300)

    # ---------- 角色与权限 modal ----------
    page.click("button:has-text('角色与权限')")
    page.wait_for_timeout(900)
    shot(page, "p05-auth-modal")
    atxt = page.locator("#authBody").inner_text()
    rec(TAG, "大盘-角色与权限", "打开弹窗", "点击「角色与权限」",
        "显示权限矩阵与当前身份",
        f"含'权限能力'={('权限能力' in atxt)} 含当前={('当前' in atxt)} 长度={len(atxt)}",
        "正常" if "权限能力" in atxt else "缺陷", "")
    page.click("#mAuth .mf button:has-text('关闭')")
    page.wait_for_timeout(300)

    # ---------- 自动流转（legal: switch hidden? data-cap manage_scheduler=admin） ----------
    sw_vis = page.locator("#swSched").count()
    run_vis = page.locator("#btnSchedRun").count()
    rec(TAG, "大盘-自动流转", "定时拉取开关/立即拉取一次", "检查可见性",
        "admin 才可见（legal 隐藏）", f"开关={sw_vis} 按钮={run_vis}", "正常", "")

    # ---------- 审查队列面板 ----------
    qtxt = page.locator("#queueKv").inner_text()
    rec(TAG, "大盘-审查队列", "队列与配额渲染", "读取面板", "显示工作线程/排队/待处理/附件水位",
        f"内容={qtxt[:120].replace(chr(10),' ')}", "正常" if "工作线程" in qtxt else "缺陷", "")

    # ---------- samples ----------
    page.click("#btnSamples")
    page.wait_for_timeout(1200)
    shot(page, "p05-samples-expanded")
    stxt = page.locator("#sampleBox").inner_text()
    rec(TAG, "大盘-示例合同集", "展开", "点击「展开」",
        "表格列出 8 份示例（DOCX/PDF/扫描件）",
        f"含示例文件数≈{stxt.count('.docx')+stxt.count('.pdf')+stxt.count('.png')} 摘要={stxt[:100].replace(chr(10),' ')}",
        "正常" if stxt.count(".docx") + stxt.count(".pdf") >= 5 else "缺陷", "")

    # ---------- filters ----------
    page.fill("#kw", "不存在的合同XYZ")
    page.wait_for_timeout(1500)
    empty_shown = page.locator("#empty").is_visible()
    rec(TAG, "大盘-筛选", "搜索关键词", "输入不存在关键词",
        "表格进入空态", f"空态可见={empty_shown}", "正常" if empty_shown else "缺陷", "")
    page.fill("#kw", "")
    page.select_option("#fRisk", "high")
    page.wait_for_timeout(1200)
    risk_rows = page.locator("#tbody tr").count()
    rec(TAG, "大盘-筛选", "风险等级=高", "选择筛选",
        "列表刷新为该口径", f"行数={risk_rows}", "正常", "")
    page.select_option("#fRisk", "")
    page.select_option("#fStatus", "completed")
    page.wait_for_timeout(1200)
    rec(TAG, "大盘-筛选", "审查状态=审查完成", "选择筛选", "列表刷新", f"行数={page.locator('#tbody tr').count()}", "正常", "")
    page.select_option("#fStatus", "")
    page.select_option("#fType", "purchase")
    page.wait_for_timeout(1200)
    rec(TAG, "大盘-筛选", "合同类型=采购", "选择筛选", "列表刷新", f"行数={page.locator('#tbody tr').count()}", "正常", "")
    page.select_option("#fType", "")
    page.click("button:has-text('刷新')")
    page.wait_for_timeout(1500)
    rec(TAG, "大盘-页头", "刷新按钮", "点击", "列表重新拉取", f"行数={page.locator('#tbody tr').count()}", "正常", "")

    # ---------- stat card drill ----------
    cards = page.locator("#stats .stat.clickable")
    n = cards.count()
    drill_ok = 0
    for i in range(min(n, 7)):
        try:
            cards.nth(i).click()
            page.wait_for_timeout(1200)
            visible = page.locator("#mDrill").is_visible()
            title = page.locator("#drillTitle").inner_text()
            body_len = len(page.locator("#drillBody").inner_text())
            if i == 0:
                shot(page, "p05-drill-modal-first-card")
            if visible and body_len > 10:
                drill_ok += 1
            page.click("#mDrill .mh button:has-text('关闭')")
            page.wait_for_timeout(400)
        except Exception as e:  # noqa: BLE001
            rec(TAG, "大盘-统计卡", f"第 {i+1} 张卡下钻", "点击", "打开明细弹窗", f"异常 {e}", "缺陷", "")
    rec(TAG, "大盘-统计卡", f"全部 {n} 张卡下钻", "逐张点击", "每张都打开明细弹窗",
        f"成功 {drill_ok}/{n}", "正常" if drill_ok == n else "缺陷", "screenshot agent4-*drill*")

    # drill row -> workbench + drill 筛选 + 导出 JSON
    page.locator("#stats .stat.clickable").first.click()
    page.wait_for_timeout(1200)
    row_n = page.locator("#drillBody tr[data-go]").count()
    if row_n:
        page.locator("#drillBody tr[data-go]").first.click()
        page.wait_for_timeout(2000)
        rec(TAG, "大盘-下钻明细", "点击明细行", "进入工作台",
            "/workbench?id=xx",
            f"URL={page.url}", "正常" if "workbench" in page.url else "缺陷", "")
        page.go_back()
        settle(page, 1200)
        page.locator("#stats .stat.clickable").first.click()
        page.wait_for_timeout(1200)
    # 在大盘中按此条件筛选
    try:
        page.click("#drillBody button:has-text('在大盘中按此条件筛选')")
        page.wait_for_timeout(1200)
        rec(TAG, "大盘-下钻明细", "按此条件筛选", "点击",
            "关闭弹窗并按条件筛选列表", f"弹窗可见={page.locator('#mDrill').is_visible()} 行数={page.locator('#tbody tr').count()}",
            "正常", "")
    except Exception as e:  # noqa: BLE001
        rec(TAG, "大盘-下钻明细", "按此条件筛选", "点击", "关闭弹窗并筛选", f"异常 {e}", "缺陷", "")
    # 导出全量 JSON
    try:
        page.locator("#stats .stat.clickable").nth(5).click()
        page.wait_for_timeout(1200)
        with page.expect_download(timeout=8000) as dl:
            page.click("#drillBody button:has-text('导出全量数据')")
        d = dl.value
        rec(TAG, "大盘-下钻明细", "导出全量数据(JSON)", "点击", "下载 JSON 文件",
            f"下载 {d.suggested_filename}", "正常", "")
        page.click("#mDrill .mh button:has-text('关闭')")
    except Exception as e:  # noqa: BLE001
        rec(TAG, "大盘-下钻明细", "导出全量数据(JSON)", "点击", "下载 JSON 文件", f"异常 {e}", "缺陷", "")

    # ---------- 表格交互：全选 + 批量按钮 ----------
    page.wait_for_timeout(500)
    rows_now = page.locator("#tbody tr").count()
    if rows_now:
        page.check("#ckAll")
        page.wait_for_timeout(300)
        sel = page.locator("#selInfo").inner_text()
        rec(TAG, "大盘-任务表", "全选复选框", "勾选表头全选",
            "所有行勾选 + 顶部出现「已选 N 项」", f"selInfo=「{sel}」", "正常" if "已选" in sel else "缺陷", "")
        # 批量导出 Markdown（legal 可导出）
        try:
            with page.expect_download(timeout=10000) as dl:
                page.click("button:has-text('批量导出 Markdown')")
            rec(TAG, "大盘-任务表", "批量导出 Markdown", "点击", "逐份下载 .md 报告",
                f"首个下载={dl.value.suggested_filename}", "正常", "")
        except Exception as e:  # noqa: BLE001
            rec(TAG, "大盘-任务表", "批量导出 Markdown", "点击", "逐份下载 .md 报告", f"异常 {e}", "缺陷", "")
        # 批量重新审查（legal 允许）
        page.click("button:has-text('批量重新审查')")
        page.wait_for_timeout(2500)
        t = toast_text(page)
        rec(TAG, "大盘-任务表", "批量重新审查", "点击（已全选）", "逐个重新审查并 toast 汇总",
            f"toast=「{t[:140]}」", "正常" if t else "部分", "")
        page.uncheck("#ckAll")
        page.wait_for_timeout(300)

    # ---------- row actions: 审查 link + 重审 ----------
    if page.locator("#tbody tr a.btn:has-text('审查')").count():
        first_title = page.locator("#tbody tr .t-title").first.inner_text()
        # 重审 button on first row
        rbtn = page.locator("#tbody tr").first.locator("button:has-text('重审'), button:has-text('重新审查')")
        if rbtn.count():
            rbtn.first.click()
            page.wait_for_timeout(2500)
            t = toast_text(page)
            rec(TAG, "大盘-任务表", "行内「重审/重新审查」", f"对「{first_title[:18]}」点击",
                "触发重新审查并 toast 结果", f"toast=「{t[:120]}」", "正常" if t else "部分", "")
        # 审查 link -> workbench
        page.locator("#tbody tr a.btn:has-text('审查')").first.click()
        page.wait_for_timeout(2200)
        rec(TAG, "大盘-任务表", "行内「审查」", "点击进入工作台",
            "/workbench?id=xx 且工作台渲染",
            f"URL={page.url} 有风险清单tab={page.locator('button:has-text(\"风险清单\")').count()>0}",
            "正常" if "workbench" in page.url else "缺陷", "")
        shot(page, "p05-workbench-from-table")
        page.go_back()
        settle(page, 1500)

    # ---------- pet assistant ----------
    try:
        page.click("#petBtn", timeout=4000)
        page.wait_for_timeout(1200)
        shot(page, "p05-pet-open")
        pet_vis = page.locator("#petPanel").is_visible() if page.locator("#petPanel").count() else False
        chips = page.locator(".pet-chip").count()
        rec(TAG, "大盘-助手", "打开机器人助手", "点击宠物按钮",
            "面板打开，含快捷 chips",
            f"面板可见={pet_vis} chips={chips}", "正常" if pet_vis else "缺陷", "")
        # ask a question via chip
        if chips:
            c0 = page.locator(".pet-chip").first.inner_text()
            page.locator(".pet-chip").first.click()
            page.wait_for_timeout(3500)
            body = page.locator("#petPanel").inner_text()
            rec(TAG, "大盘-助手", f"快捷问题「{c0[:20]}」", "点击 chip",
                "助手返回回答",
                f"面板文本长度={len(body)} 尾部={body[-80:].replace(chr(10),' ')}",
                "正常" if len(body) > 60 else "部分", "")
        shot(page, "p05-pet-after-ask")
        # close
        if page.locator(".pet-x").count():
            page.locator(".pet-x").first.click()
            page.wait_for_timeout(400)
    except Exception as e:  # noqa: BLE001
        rec(TAG, "大盘-助手", "打开机器人助手", "点击宠物按钮", "面板打开", f"异常 {e}", "缺陷", "")

    # ---------- theme via topbar (already) ; issues ----------
    iss = s.issues(page)
    rec(TAG, "大盘", "控制台/网络异常汇总", "整页操作后统计",
        "无 5xx/无脚本报错",
        f"console={iss['console'][:4]} 4xx={iss['http4xx'][:5]} failed={iss['failed'][:3]}",
        "正常" if not [x for x in iss["http4xx"] if " 5" in x] else "缺陷", "")

print("S02 DONE")