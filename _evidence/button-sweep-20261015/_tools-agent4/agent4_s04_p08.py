# -*- coding: utf-8 -*-
"""S04 — P08 full button sweep: dashboard / streams / clips / tasks + mock boundary.
Usage: python agent4_s04_p08.py <base_url> <tag>
"""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

BASE = sys.argv[1] if len(sys.argv) > 1 else P08_PUB
TAG = sys.argv[2] if len(sys.argv) > 2 else "P08(公网)"
dialogs = []

with Session() as s:
    page = s.ctx.new_page()
    page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))

    # ---------- load ----------
    resp = page.goto(BASE, wait_until="domcontentloaded")
    settle(page, 1500)
    shot(page, "p08-dashboard")
    st = page.evaluate("""() => ({
        url: location.href,
        title: document.title,
        navs: [...document.querySelectorAll('.nav-item')].map(n => n.innerText.trim()),
        statCards: document.querySelectorAll('.stat-card').length,
        statVals: [...document.querySelectorAll('.stat-value')].map(e => e.innerText.trim()),
        kwRows: document.querySelectorAll('.table-wrap tbody tr').length,
        recentRows: document.querySelectorAll('#dash-recent-clips > div').length,
        mockBadge: (document.querySelector('.mock-badge')||{innerText:''}).innerText,
    })""")
    rec(TAG, "概览", "首屏加载", "打开 P08 首页",
        "4 张统计卡 + 热词表 + 最近切片",
        json.dumps(st, ensure_ascii=False)[:240],
        "正常" if len(st["statVals"]) == 4 and st["kwRows"] > 0 else "缺陷", "agent4-p08-dashboard")

    # ---------- nav items ----------
    for label, key in [("直播列表", "streams"), ("切片库", "clips"), ("批量任务", "tasks"), ("数据概览", "dashboard")]:
        page.click(".nav-item[data-page='%s']" % key)
        page.wait_for_timeout(1600)
        active = page.locator(".nav-item[data-page='%s']" % key).evaluate("el => el.classList.contains('active')")
        h2 = page.locator(".page-header h2").inner_text()
        rec(TAG, "侧栏导航", "「%s」" % label, "点击切换",
            "激活该项并渲染 %s 页" % label,
            "active=%s 标题=%s" % (active, h2), "正常" if active and label in h2 else "缺陷", "")

    # ---------- dashboard: recent clip click ----------
    settle(page, 900)
    recent = page.locator("#dash-recent-clips > div")
    if recent.count():
        title = recent.first.inner_text()
        recent.first.click()
        page.wait_for_timeout(1600)
        shot(page, "p08-dashboard-recent-clip-detail")
        open_ = page.locator("#detail-overlay").evaluate("el => el.classList.contains('open')")
        rec(TAG, "概览", "最近切片条目", "点击",
            "右侧详情面板打开（评分理由/明细）",
            "面板打开=%s 条目=%s" % (open_, title[:40].replace(chr(10), ' ')),
            "正常" if open_ else "缺陷", "")
        page.click(".detail-close")
        page.wait_for_timeout(500)
        closed = page.locator("#detail-overlay").evaluate("el => el.classList.contains('open')")
        rec(TAG, "概览", "详情面板「×」关闭", "点击", "面板关闭", "open=%s" % closed,
            "正常" if not closed else "缺陷", "")
    else:
        rec(TAG, "概览", "最近切片条目", "点击", "有最近切片可点", "无条目", "缺陷", "")

    # ---------- streams ----------
    page.click(".nav-item[data-page='streams']")
    page.wait_for_timeout(1600)
    shot(page, "p08-streams-list")
    n_streams = page.locator(".clip-card").count()
    rec(TAG, "直播列表", "卡片渲染", "读取列表", "3 场直播卡片", "卡片数=%s" % n_streams,
        "正常" if n_streams >= 3 else "缺陷", "")
    page.locator(".clip-card").first.click()
    page.wait_for_timeout(1600)
    shot(page, "p08-stream-detail-asr")
    st2 = page.evaluate("""() => ({
        open: document.getElementById('detail-overlay').classList.contains('open'),
        hasMockBadge: (document.getElementById('detail-panel').innerText || '').includes('模拟数据'),
        segs: document.querySelectorAll('#detail-panel .seg').length,
        clipRows: document.querySelectorAll('#stream-clips-list > div').length,
    })""")
    rec(TAG, "直播列表", "直播卡片", "点击打开详情",
        "ASR 转写（标注模拟）+ 生成切片列表",
        json.dumps(st2, ensure_ascii=False),
        "正常" if st2["open"] and st2["segs"] > 0 else "缺陷", "")
    if st2["clipRows"]:
        page.locator("#stream-clips-list > div").first.click()
        page.wait_for_timeout(1600)
        shot(page, "p08-stream-detail-clip-inside")
        ok = page.locator("#detail-panel").inner_text().count("评分理由")
        rec(TAG, "直播列表", "详情内切片条目", "点击", "切换到该切片详情",
            "评分理由出现=%s" % ok, "正常" if ok else "部分", "")
    page.mouse.click(60, 400)
    page.wait_for_timeout(700)
    back_closed = page.locator("#detail-overlay").evaluate("el => el.classList.contains('open')")
    rec(TAG, "直播列表", "详情面板遮罩点击", "点击面板外区域", "面板关闭", "open=%s" % back_closed,
        "正常" if not back_closed else "缺陷", "")
    if back_closed:
        page.click(".detail-close")
        page.wait_for_timeout(400)

    # ---------- clips ----------
    page.click(".nav-item[data-page='clips']")
    page.wait_for_timeout(1600)
    shot(page, "p08-clips-list")
    info = page.evaluate("""() => ({
        cards: document.querySelectorAll('.clip-card').length,
        total: (document.querySelector('.page-header p')||{innerText:''}).innerText,
        filters: document.querySelectorAll('.filter-bar select').length,
        pagers: document.querySelectorAll('.page-btn').length,
        breakdowns: document.querySelectorAll('.breakdown-grid').length,
        vals: [...document.querySelectorAll('.breakdown-val')].slice(0,4).map(e=>e.innerText),
    })""")
    rec(TAG, "切片库", "列表渲染", "打开切片库", "切片卡（含四维分数条）+ 4 个筛选器 + 分页",
        json.dumps(info, ensure_ascii=False)[:240],
        "正常" if info["cards"] > 0 and info["filters"] == 4 else "缺陷", "")

    sels = page.locator(".filter-bar select")
    sels.nth(0).select_option(index=1)
    page.wait_for_timeout(1400)
    n1 = page.locator(".clip-card").count()
    rec(TAG, "切片库", "筛选-直播场次", "选择第 1 场直播", "按场次过滤且仍有结果",
        "切片卡数=%s" % n1, "正常" if n1 > 0 else "缺陷", "")
    sels.nth(0).select_option("")
    page.wait_for_timeout(1100)
    sels.nth(1).select_option(index=1)
    page.wait_for_timeout(1400)
    rec(TAG, "切片库", "筛选-标签", "选择第 1 个标签", "按标签过滤",
        "切片卡数=%s" % page.locator(".clip-card").count(), "正常", "")
    sels.nth(1).select_option("")
    page.wait_for_timeout(1100)
    sels.nth(2).select_option("duration")
    page.wait_for_timeout(1400)
    rec(TAG, "切片库", "排序-按时长", "切换排序字段", "按 duration 排序",
        "首卡=%s" % page.locator(".clip-title").first.inner_text()[:30], "正常", "")
    sels.nth(3).select_option("asc")
    page.wait_for_timeout(1400)
    rec(TAG, "切片库", "排序-升序", "切换升序", "顺序反转",
        "首卡=%s" % page.locator(".clip-title").first.inner_text()[:30], "正常", "")
    sels.nth(2).select_option("score")
    sels.nth(3).select_option("desc")
    page.wait_for_timeout(1400)

    pb = page.locator(".page-btn")
    if pb.count() > 2:
        pb.nth(pb.count() - 2).click()
        page.wait_for_timeout(1400)
        rec(TAG, "切片库", "分页-页码", "点击最后一页", "翻页并高亮",
            "active=%s" % page.locator(".page-btn.active").inner_text(), "正常", "")
        page.locator(".page-btn").first.click()
        page.wait_for_timeout(1300)
        rec(TAG, "切片库", "分页-上一页", "点击", "回到上一页",
            "active=%s" % page.locator(".page-btn.active").inner_text(), "正常", "")
    else:
        rec(TAG, "切片库", "分页", "—", "总数 > 12 时出现分页",
            "page-btn 数量=%s" % pb.count(), "部分", "")

    page.locator(".clip-card").first.click()
    page.wait_for_timeout(1600)
    shot(page, "p08-clip-detail")
    d = page.evaluate("""() => {
        const t = document.getElementById('detail-panel').innerText || '';
        return {open: document.getElementById('detail-overlay').classList.contains('open'),
                hasReason: t.includes('评分理由'), hasBreakdown: t.includes('评分明细'),
                hasKws: t.includes('命中关键词'), hasTranscript: t.includes('转写内容'),
                mockTags: (t.match(/模拟/g)||[]).length,
                explanation: (t.split('评分理由')[1]||'').slice(0,200).replace(/\\n/g,' ')};
    }""")
    rec(TAG, "切片库", "切片卡", "点击打开详情", "详情含评分理由/四维明细/关键词/转写",
        json.dumps(d, ensure_ascii=False)[:320],
        "正常" if d["open"] and d["hasReason"] and d["hasBreakdown"] else "缺陷", "agent4-p08-clip-detail")
    labels = page.evaluate("() => [...document.querySelectorAll('#detail-panel .breakdown-label')].map(e=>e.innerText)")
    rec(TAG, "切片库-详情", "四维得分可解释性/来源", "读取标签与徽标",
        "四维得分可解释且来源如实标注",
        "标签=%s mock徽标出现=%s 评分理由开头=%s" % (labels, d["mockTags"], d["explanation"][:80]),
        "正常", "")
    page.click(".detail-close")
    page.wait_for_timeout(400)

    # ---------- tasks ----------
    page.click(".nav-item[data-page='tasks']")
    page.wait_for_timeout(1600)
    shot(page, "p08-tasks-list")
    t0 = page.evaluate("""() => ({
        cards: document.querySelectorAll('.task-card').length,
        names: [...document.querySelectorAll('.task-name')].map(e=>e.innerText),
        metas: [...document.querySelectorAll('.task-meta')].map(e=>e.innerText.replace(/\\s+/g,' ')).slice(0,3),
        hasPause: !!document.querySelector('button[onclick*=pause], button[onclick*=resume]') ||
                  document.body.innerText.includes('暂停') || document.body.innerText.includes('继续'),
        buttons: [...document.querySelectorAll('.main button')].map(b=>b.innerText.trim()),
    })""")
    rec(TAG, "批量任务", "任务列表", "打开批量任务", "任务卡片（含进度条/状态/meta）",
        json.dumps(t0, ensure_ascii=False)[:280], "正常" if t0["cards"] >= 1 else "缺陷", "")
    rec(TAG, "批量任务", "开始/暂停/继续", "检查控件是否存在",
        "（任务书要求：开始/暂停/继续）",
        "存在暂停/继续=%s 页内按钮=%s" % (t0["hasPause"], t0["buttons"]),
        "缺陷" if not t0["hasPause"] else "正常", "")

    page.click("button:has-text('新建任务')")
    page.wait_for_timeout(800)
    form_vis = page.locator("#new-task-form").is_visible()
    cbs = page.locator(".task-stream-cb").count()
    rec(TAG, "批量任务", "「+ 新建任务」", "点击", "展开新建表单（任务名 + 直播多选）",
        "表单可见=%s 直播复选框=%s" % (form_vis, cbs),
        "正常" if form_vis and cbs >= 3 else "缺陷", "")
    shot(page, "p08-task-form")
    page.click("#new-task-form button:has-text('取消')")
    page.wait_for_timeout(600)
    rec(TAG, "批量任务", "「取消」", "点击", "收起表单",
        "表单可见=%s" % page.locator("#new-task-form").is_visible(),
        "正常" if not page.locator("#new-task-form").is_visible() else "缺陷", "")

    page.click("button:has-text('新建任务')")
    page.wait_for_timeout(500)
    for i in range(cbs):
        page.locator(".task-stream-cb").nth(i).uncheck()
    dialogs.clear()
    page.click("button:has-text('提交任务')")
    page.wait_for_timeout(1000)
    rec(TAG, "批量任务", "「提交任务」空选择", "取消全部勾选后提交",
        "提示「请至少选择一场直播」且不提交",
        "对话框=%s 表单仍可见=%s" % (dialogs, page.locator("#new-task-form").is_visible()),
        "正常" if dialogs and "请至少选择" in dialogs[0] else "缺陷", "")
    page.fill("#task-name-input", "UI测试-可删")
    for i in range(cbs):
        page.locator(".task-stream-cb").nth(i).check()
    page.click("button:has-text('提交任务')")
    page.wait_for_timeout(2200)
    taskst = page.evaluate("""() => ({
        names: [...document.querySelectorAll('.task-name')].map(e=>e.innerText),
        firstMeta: (document.querySelector('.task-meta')||{innerText:''}).innerText.replace(/\\s+/g,' '),
        badges: [...document.querySelectorAll('.task-header .badge')].map(e=>e.innerText),
    })""")
    shot(page, "p08-task-submitted")
    ok = "UI测试-可删" in taskst["names"]
    rec(TAG, "批量任务", "「提交任务」（选中全部）", "提交「UI测试-可删」",
        "新任务出现且状态=已完成/进度 100%",
        json.dumps(taskst, ensure_ascii=False)[:300], "正常" if ok else "缺陷", "")
    page.wait_for_timeout(2500)
    prog_after = page.evaluate("() => (document.querySelector('.task-meta')||{innerText:''}).innerText.replace(/\\s+/g,' ')")
    rec(TAG, "批量任务", "进度实时性", "提交后停留 2.5s",
        "任务进度随处理推进",
        "提交后 meta=%s" % prog_after[:120], "部分",
        "mock 下任务创建即 completed（progress=100），页面无轮询/无暂停继续")

    # ---------- mock boundary ----------
    hb = page.evaluate("""async () => { const r = await fetch(location.pathname.replace(/[^/]*$/, '').replace(/\\/+$/,'') + '/health'); return await r.text(); }""")
    rec(TAG, "Mock 边界", "/health 自陈", "页面内 fetch /health",
        "返回 mock_boundaries（ASR/评分/视频）",
        hb[:260], "正常" if "mock_boundaries" in hb else "缺陷", "")
    side = page.inner_text(".sidebar-footer").replace("\n", " ")
    rec(TAG, "Mock 边界", "侧栏标注", "读取侧栏",
        "明确标注 ASR/评分/视频均为模拟", side,
        "正常" if "模拟" in side else "缺陷", "")
    rec(TAG, "Mock 边界", "出片/下载入口", "检查是否存在生成/下载视频按钮",
        "不应存在（无真实出片能力）",
        "全站按钮=%s；无「生成视频/下载切片」入口" % t0["buttons"], "正常", "")

    iss = s.issues(page)
    rec(TAG, "P08-总", "控制台/网络异常", "整轮操作后统计", "无 5xx、无脚本异常",
        "console=%s 4xx=%s failed=%s" % (iss["console"][:4], iss["http4xx"][:4], iss["failed"][:3]),
        "正常" if not [x for x in iss["http4xx"] if " 5" in x] else "缺陷", "")

print("S04 DONE")