/* Agent5 · P07 AI 素材中心 按钮全量点击测试（只测不改）
 * 运行: node agent5-p07-sweep.js  (workdir 需含 node_modules/playwright)
 * env: P07_BASE (默认公网 /p07/), P07_TAG (默认 public)
 * 纪律: 只创建「UI测试-可删」资产并全部删除；不动种子数据；不碰 ingest UI
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const EVID = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.P07_BASE || 'http://39.96.200.45:8090/p07/';
const TAG = process.env.P07_TAG || 'public';
const UPLOAD_SRC = 'D:\\software\\PycharmProjects\\作品矩阵\\projects\\p07-ai-asset-center\\data\\uploads\\AST-18356A.png';

const started = new Date().toISOString();
const steps = [];
const consoleMsgs = [];
const netFails = [];
const apiDumps = [];
let shotN = 1;
let lastDialog = null;

function rec(pageName, widget, action, expected, actual, verdict, evidence) {
  steps.push({ ts: new Date().toISOString(), page: pageName, widget, action, expected, actual: String(actual).slice(0, 1800), verdict, evidence });
  console.log(`[${verdict}] ${pageName} | ${widget} | ${action} | ${String(actual).slice(0, 180)}`);
}
async function shot(page, desc, fullPage) {
  const name = `agent5-${String(shotN).padStart(2, '0')}-p07-${TAG}-${desc}.png`;
  shotN++;
  try { await page.screenshot({ path: path.join(EVID, name), fullPage: !!fullPage, timeout: 20000, animations: 'disabled' }); }
  catch (e) { console.log('screenshot fail', name, e.message); }
  return name;
}
function J(x, n) { try { return JSON.stringify(x).slice(0, n || 700); } catch (e) { return String(x); } }

const watchdog = setTimeout(() => {
  try { fs.writeFileSync(path.join(EVID, `agent5-p07-${TAG}-partial.json`), JSON.stringify({ base: BASE, tag: TAG, note: 'watchdog', steps, consoleMsgs, netFails, apiDumps }, null, 2), 'utf-8'); } catch (e) { }
  console.error('WATCHDOG: partial dumped, exiting');
  process.exit(2);
}, 900000);

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1560, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(60000);
  page.on('dialog', async d => { lastDialog = d.message(); await d.accept().catch(() => { }); });

  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') consoleMsgs.push({ type: m.type(), text: m.text().slice(0, 400), url: (m.location() || {}).url || '' }); });
  page.on('pageerror', e => consoleMsgs.push({ type: 'pageerror', text: String(e).slice(0, 400) }));
  page.on('requestfailed', r => netFails.push({ url: r.url().slice(0, 260), err: (r.failure() || {}).errorText || '' }));
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/api/v1/')) {
      let body = null;
      if (!u.includes('/file')) { try { body = JSON.stringify(await r.json()).slice(0, 5000); } catch (e) { } }
      apiDumps.push({ ts: new Date().toISOString(), url: u.slice(0, 260), status: r.status(), m: r.request().method(), body });
    }
  });
  const waitResp = (part, method, timeout) => page.waitForResponse(r => r.url().includes(part) && (!method || r.request().method() === method), { timeout: timeout || 60000 });

  try {
    /* ── 0. 首屏 + 状态徽章 ──────────────────────────────── */
    const resp = await page.goto(BASE, { waitUntil: 'load', timeout: 60000 });
    await page.waitForFunction(() => (document.getElementById('status-badges').innerText || '').length > 0, null, { timeout: 30000 }).catch(() => { });
    await page.waitForTimeout(1500);
    const head = await page.evaluate(() => ({
      badges: document.getElementById('status-badges').innerText.replace(/\n/g, ' ; '),
      navTabs: [...document.querySelectorAll('#nav .tab')].map(t => t.dataset.page),
      metricCards: [...document.querySelectorAll('#content .card')].slice(0, 4).map(c => c.innerText.replace(/\n/g, '=').slice(0, 80)),
      note: (document.querySelector('#content p.mt-4') || {}).innerText || '',
    }));
    rec('概览', '页面加载', `打开 ${BASE}`, '首屏渲染 + LLM 状态徽章', `HTTP ${resp.status()}；badges="${head.badges}"；nav=${head.navTabs.join('/')}`, resp.status() === 200 ? '正常' : '缺陷', await shot(page, 'dashboard'));
    // 图表渲染（echarts 懒加载）
    let canvases = 0;
    try { await page.waitForFunction(() => document.querySelectorAll('#content canvas').length >= 6, null, { timeout: 90000 }); } catch (e) { }
    canvases = await page.evaluate(() => document.querySelectorAll('#content canvas').length);
    rec('概览', '图表渲染（6 图）', '等待 echarts 懒加载并画图', '6 张图全部渲染出 canvas', `canvas=${canvases}；卡片=${J(head.metricCards, 400)}`, canvases >= 6 ? '正常' : '缺陷', await shot(page, 'dashboard-charts'));

    /* ── 1. 素材库：上传（真实文件 + 智能打标） ───────────── */
    await page.click('#nav .tab[data-page="library"]');
    await page.waitForSelector('#up-name', { timeout: 30000 });
    await page.waitForTimeout(500);
    const libInit = await page.evaluate(() => ({
      libCount: (document.getElementById('lib-count') || {}).innerText || '',
      autotag: document.getElementById('up-autotag').checked,
      autotagLabel: document.getElementById('up-autotag').parentElement.innerText.trim().slice(0, 80),
    }));
    rec('素材库', '进入 Tab', '点击侧栏「素材库」', '显示上传表单+素材网格', `${libInit.libCount}；自动打标勾选=${libInit.autotag}（${libInit.autotagLabel}）`, '正常', await shot(page, 'library-initial'));

    await page.fill('#up-name', 'UI测试-可删-夏季控油防晒喷雾主图');
    await page.selectOption('#up-type', 'image');
    await page.fill('#up-tags', '防晒,夏季,控油,UI测试');
    await page.fill('#up-desc', 'UI测试素材（可删）：夏天清爽的防晒喷雾，用于以文搜图命中验证');
    await page.setInputFiles('#up-file', UPLOAD_SRC);
    await page.waitForTimeout(300);
    const dropInfo = await page.$eval('#drop-info', el => el.innerText);
    rec('素材库', '文件选择', `选中 ${path.basename(UPLOAD_SRC)}`, '显示已选文件与大小', dropInfo, dropInfo.includes('已选') ? '正常' : '缺陷', await shot(page, 'library-form-filled'));

    const upRespP = waitResp('/api/v1/assets', 'POST', 120000);
    await page.click('button:has-text("上传入库")');
    let upStatus = -1, upBody = null;
    try { const r = await upRespP; upStatus = r.status(); upBody = await r.json(); } catch (e) { upBody = { err: e.message.slice(0, 200) }; }
    const upId = upBody && upBody.asset_id;
    const tg = upBody && upBody.tagging || {};
    try { await page.waitForFunction(() => (document.getElementById('asset-grid') || {}).innerText.includes('UI测试-可删-夏季控油防晒喷雾主图'), null, { timeout: 30000 }); } catch (e) { }
    const upToast = await page.$eval('#toast', el => el.innerText).catch(() => '');
    rec('素材库', '「上传入库」按钮', '上传 PNG + 自动打标', '201 入库；真实打标或如实降级', `HTTP ${upStatus}；asset_id=${upId}；tag_source=${tg.tag_source}；tags=${J(tg.tags)}；degraded=${tg.degraded_reason || '-'}；宽高=${upBody && upBody.width}x${upBody && upBody.height}；file_url=${upBody && upBody.file_url}；toast="${upToast}"`, (upStatus === 201 && upId) ? (tg.tag_source === 'llm' ? '正常' : '部分') : '缺陷', await shot(page, 'library-upload-done'));

    // 上传空名校验（点上传不填名）
    await page.evaluate(() => { document.getElementById('up-name').value = ''; });
    await page.click('button:has-text("上传入库")');
    await page.waitForTimeout(400);
    const emptyToast = await page.$eval('#toast', el => el.innerText).catch(() => '');
    rec('素材库', '上传校验', '不填名称点上传', '提示「请填写素材名称」', `toast="${emptyToast}"`, emptyToast.includes('请填写素材名称') ? '正常' : '缺陷', '');

    // 素材库搜索/筛选/重置
    await page.fill('#kw', '防晒');
    const libSearchP = waitResp('/api/v1/assets?', 'GET', 30000);
    await page.click('button:has-text("搜索")');
    try { await libSearchP; } catch (e) { }
    await page.waitForTimeout(400);
    const kwCount = await page.$eval('#lib-count', el => el.innerText).catch(() => '');
    rec('素材库', '搜索按钮', '关键字「防晒」', '按关键字过滤', kwCount, '正常', '');
    await page.selectOption('#type-filter', 'copy');
    const libTypeP = waitResp('/api/v1/assets?', 'GET', 30000);
    await page.click('button:has-text("搜索")');
    try { await libTypeP; } catch (e) { }
    await page.waitForTimeout(400);
    const typeCount = await page.$eval('#lib-count', el => el.innerText).catch(() => '');
    rec('素材库', '类型筛选', 'type=copy + 关键字', '仅文案类', typeCount, '正常', '');
    const resetP = waitResp('/api/v1/assets?', 'GET', 30000);
    await page.click('button:has-text("重置")');
    try { await resetP; } catch (e) { }
    await page.waitForTimeout(400);
    const resetCount = await page.$eval('#lib-count', el => el.innerText).catch(() => '');
    rec('素材库', '重置按钮', '点击重置', '恢复全量列表', resetCount, '正常', '');

    /* ── 2. 以文搜图 ─────────────────────────────────────── */
    await page.click('#nav .tab[data-page="search"]');
    await page.waitForSelector('#search-q', { timeout: 30000 });
    rec('以文搜图', '进入 Tab', '点击侧栏「以文搜图」', '显示检索框+示例词', '检索框/示例词渲染', '正常', await shot(page, 'search-initial'));

    // 2a. 命中：中文查询（点示例词）
    const s1P = waitResp('/api/v1/search', 'POST', 60000);
    await page.click('button:has-text("夏天清爽的防晒霜")');
    let s1 = null; try { s1 = await (await s1P).json(); } catch (e) { s1 = { err: e.message.slice(0, 150) }; }
    await page.waitForTimeout(500);
    const s1ui = await page.$eval('#search-results', el => el.innerText.replace(/\n/g, ' | ').slice(0, 500));
    const hitMine = !!(s1 && s1.items && upId && s1.items.some(i => i.asset_id === upId));
    rec('以文搜图', '搜索按钮/示例词（命中）', '查询「夏天清爽的防晒霜」', '命中相关素材（含刚上传的图）', `refused=${s1 && s1.refused}；total=${s1 && s1.total}；threshold=${s1 && s1.threshold}；query_terms=${J(s1 && s1.query_terms)}；包含刚传素材=${hitMine}；items=${J(s1 && s1.items && s1.items.map(i => ({ id: i.asset_id, n: i.name, rel: i.relevance_score })), 500)}；UI="${s1ui.slice(0, 220)}"`, (s1 && !s1.refused && s1.total > 0) ? (hitMine ? '正常' : '部分') : '缺陷', await shot(page, 'search-hit'));

    // 2b. 拒答：无关查询（示例词）
    const s2P = waitResp('/api/v1/search', 'POST', 60000);
    await page.click('button:has-text("库里没有的无人机航拍素材")');
    let s2 = null; try { s2 = await (await s2P).json(); } catch (e) { s2 = { err: e.message.slice(0, 150) }; }
    await page.waitForTimeout(500);
    const s2ui = await page.$eval('#search-results', el => el.innerText.replace(/\n/g, ' | ').slice(0, 400));
    rec('以文搜图', '搜索（拒答）', '查询「库里没有的无人机航拍素材」', 'refused=true 且说明原因', `refused=${s2 && s2.refused}；reason=${s2 && s2.reason}；query_terms=${J(s2 && s2.query_terms)}；UI="${s2ui.slice(0, 200)}"`, (s2 && s2.refused) ? '正常' : '缺陷', await shot(page, 'search-refused'));

    // 2c. 类型筛选 + TopN
    await page.selectOption('#search-type', 'image');
    await page.selectOption('#search-k', '10');
    const s3P = waitResp('/api/v1/search', 'POST', 60000);
    await page.fill('#search-q', '夏天清爽的防晒霜');
    await page.click('#content .btn-primary:has-text("搜索")');
    let s3 = null; try { s3 = await (await s3P).json(); } catch (e) { s3 = { err: e.message.slice(0, 150) }; }
    rec('以文搜图', '类型筛选 + TopN', 'type=image, Top10', '只返回图片类', `refused=${s3 && s3.refused}；total=${s3 && s3.total}；类型=${J(s3 && s3.items && [...new Set(s3.items.map(i => i.asset_type))])}`, (s3 && !s3.refused) ? '正常' : '部分', '');

    /* ── 3. AI 生成：image（mock 标注） + copy（真实 LLM） ── */
    await page.click('#nav .tab[data-page="generate"]');
    await page.waitForSelector('#gen-prompt', { timeout: 30000 });
    const genNote = await page.$eval('#content .note', el => el.innerText).catch(() => '');
    rec('AI 生成', '进入 Tab', '点击侧栏「AI 生成」', '页面标注图片为程序化绘制（mock）', `note="${genNote.slice(0, 200)}"`, genNote.includes('程序化') && genNote.includes('不是 AI 出图') ? '正常' : '部分', await shot(page, 'generate-initial'));

    // 3a. image（程序化规格卡）— save 勾选
    await page.fill('#gen-prompt', 'UI测试-可删：618大促防晒喷雾主图规格卡');
    await page.selectOption('#gen-type', 'image');
    await page.check('#gen-save');
    const g1P = waitResp('/api/v1/generate', 'POST', 180000);
    await page.click('#content button:has-text("生成")');
    let g1 = null; try { g1 = await (await g1P).json(); } catch (e) { g1 = { err: e.message.slice(0, 200) }; }
    await page.waitForTimeout(800);
    const g1ui = await page.evaluate(() => ({
      badges: [...document.querySelectorAll('#gen-result .badge')].map(b => b.innerText),
      note: (document.querySelector('#gen-result p.mt-3.text-xs') || {}).innerText || '',
      saved: (document.querySelector('#gen-result a') || {}).innerText || '',
      hasImg: !!document.querySelector('#gen-result img'),
    }));
    const genId = g1 && g1.saved_asset && g1.saved_asset.asset_id;
    rec('AI 生成', '「生成」按钮（图片/mock）', 'prompt=618大促主图规格卡, type=image, 保存勾选', '程序化规格卡 + UI 标注 mock + 入库', `source=${g1 && g1.source}；content_type=${g1 && g1.content_type}；note="${g1 && g1.note}"；badges=${J(g1ui.badges)}；noteUI="${g1ui.note.slice(0, 120)}"；saved=${genId}；hasImg=${g1ui.hasImg}`, (g1 && g1.source === 'programmatic' && g1ui.badges.join().includes('程序化')) ? '正常' : '部分', await shot(page, 'generate-image-mock'));

    // 3b. copy（真实 LLM）— save 不勾选
    await page.uncheck('#gen-save');
    await page.fill('#gen-prompt', 'UI测试-可删：夏季防晒喷雾卖点文案，3条');
    await page.selectOption('#gen-type', 'copy');
    const g2P = waitResp('/api/v1/generate', 'POST', 240000);
    await page.click('#content button:has-text("生成")');
    let g2 = null; try { g2 = await (await g2P).json(); } catch (e) { g2 = { err: e.message.slice(0, 200) }; }
    await page.waitForTimeout(800);
    const g2ui = await page.evaluate(() => ({
      badge: ([...document.querySelectorAll('#gen-result .badge')].map(b => b.innerText) || []).join('|'),
      meta: [...document.querySelectorAll('#gen-result .text-xs')].map(e => e.innerText).join(' ; ').slice(0, 300),
      saved: !!document.querySelector('#gen-result a'),
    }));
    rec('AI 生成', '「生成」按钮（文案/真实 LLM）', 'prompt=防晒喷雾卖点文案, type=copy, 不保存', '真实 LLM 生成或如实降级为规则模板', `source=${g2 && g2.source}；content_type=${g2 && g2.content_type}；meta=${J(g2 && g2.meta)}；badge="${g2ui.badge}"；saved=${g2ui.saved}；err=${g2 && g2.err}`, (g2 && (g2.source === 'llm' || g2.source === 'rule')) ? (g2.source === 'llm' ? '正常' : '部分') : '缺陷', await shot(page, 'generate-copy-real'));

    /* ── 4. 效果关联报表 ─────────────────────────────────── */
    await page.click('#nav .tab[data-page="report"]');
    await page.waitForSelector('#perf-platform', { timeout: 60000 });
    await page.waitForTimeout(1500);
    const rep1 = await page.evaluate(() => ({
      total: (document.body.innerText.match(/共 (\d+) 条关联记录/) || [])[1],
      srcUrl: (() => { const c = document.querySelector('#content code'); return c ? c.innerText : ''; })(),
      pmCards: [...document.querySelectorAll('#content .card .card p.text-xl')].map(e => e.closest('.card').innerText.replace(/\n/g, '=').slice(0, 90)),
      unavailable: (document.querySelector('#content .note') || {}).innerText || '',
    }));
    const rep1dump = apiDumps.filter(d => d.url.includes('/reports/performance') && !d.url.includes('with_platform_metrics=false')).slice(-1)[0] || {};
    let rep1pm = null; try { rep1pm = JSON.parse(rep1dump.body || 'null'); } catch (e) { }
    const pm = rep1pm && rep1pm.platform_metrics || {};
    rec('效果关联', '进入 Tab（大盘对照）', '点击侧栏「效果关联」', '真实调用 P06 指标（available + source_url）', `接口: platform_metrics.available=${pm.available}；source_url=${pm.source_url}；fetched_at=${pm.fetched_at}；reason=${pm.reason || '-'}；metrics=${J(pm.metrics && pm.metrics.map(x => x.name), 300)}；页面src文本="${rep1.srcUrl}"；页面不可用提示="${rep1.unavailable.slice(0, 100)}"`, pm.available ? '正常' : '部分', await shot(page, 'report-platform-metrics'));

    const rep2P = waitResp('/reports/performance', 'GET', 60000);
    await page.selectOption('#perf-platform', 'douyin');
    let rep2 = null; try { rep2 = await (await rep2P).json(); } catch (e) { rep2 = { err: e.message.slice(0, 150) }; }
    await page.waitForTimeout(500);
    const rep2ui = await page.evaluate(() => (document.body.innerText.match(/共 (\d+) 条关联记录/) || [])[1]);
    rec('效果关联', '平台筛选 select', '选择 抖音', '只显示抖音平台记录', `接口total=${rep2 && rep2.total}；页面计数=${rep2ui}；平台字段=${J(rep2 && rep2.items && [...new Set(rep2.items.map(i => i.platform))])}`, (rep2 && rep2.items && rep2.items.every(i => i.platform === 'douyin')) ? '正常' : '缺陷', await shot(page, 'report-filter-douyin'));

    /* ── 5. 素材详情：预览/投放录入/打标/删除（上传的那条） ── */
    if (upId) {
      await page.evaluate(id => { location.hash = 'asset/' + id; }, upId);
      await page.waitForFunction(() => document.body.innerText.includes('素材信息'), null, { timeout: 30000 });
      await page.waitForTimeout(1200);
      const det = await page.evaluate(() => {
        const img = document.querySelector('#content img');
        return { imgOk: !!img && img.complete && img.naturalWidth > 0, imgSrc: img ? img.getAttribute('src') : '', tagBadge: ([...document.querySelectorAll('#content .badge')].map(b => b.innerText).join(' | ')).slice(0, 200), perf: (document.body.innerText.match(/投放效果（(\d+) 条）/) || [])[1] };
      });
      rec('素材详情', '深链打开 + 文件预览', `#asset/${upId}`, 'file 接口真实出图（naturalWidth>0）', `imgOk=${det.imgOk}；src=${det.imgSrc}；标签徽章=${det.tagBadge}；投放条数=${det.perf}`, det.imgOk ? '正常' : '缺陷', await shot(page, 'asset-detail'));

      // 投放录入（合法）
      await page.click('button:has-text("录入投放数据")');
      await page.fill('#pf-store', 'UI测试-可删门店');
      await page.selectOption('#pf-platform', 'douyin');
      await page.fill('#pf-imp', '40000'); await page.fill('#pf-clk', '2500'); await page.fill('#pf-cvt', '100');
      await page.fill('#pf-spend', '1500'); await page.fill('#pf-rev', '12000');
      const p1P = waitResp(`/api/v1/assets/${upId}/performance`, 'POST', 60000);
      await page.click('button:has-text("提交")');
      let p1 = null; try { const r = await p1P; p1 = { status: r.status(), body: await r.json().catch(() => null) }; } catch (e) { p1 = { err: e.message.slice(0, 150) }; }
      await page.waitForTimeout(600);
      const perfRows = await page.evaluate(() => document.querySelectorAll('#content table tbody tr').length);
      rec('素材详情', '「提交」投放数据（合法）', '店铺=UI测试-可删门店, 曝光40000/点击2500/转化100/花费1500/收入12000', '201 入库并出现在表格', `HTTP=${p1.status}；页面投放行=${perfRows}；body=${J(p1.body, 260)}`, (p1.status === 201 && perfRows >= 1) ? '正常' : '缺陷', await shot(page, 'asset-perf-saved'));

      // 投放录入（非法：点击>曝光 → 422）
      await page.click('button:has-text("录入投放数据")');
      await page.fill('#pf-imp', '100'); await page.fill('#pf-clk', '900');
      const p2P = waitResp(`/api/v1/assets/${upId}/performance`, 'POST', 60000);
      await page.click('button:has-text("提交")');
      let p2 = null; try { const r = await p2P; p2 = { status: r.status(), body: await r.json().catch(() => null) }; } catch (e) { p2 = { err: e.message.slice(0, 150) }; }
      await page.waitForTimeout(400);
      const p2toast = await page.$eval('#toast', el => el.innerText).catch(() => '');
      rec('素材详情', '「提交」投放数据（非法载荷）', '点击900 > 曝光100', '后端 422 拒绝并提示', `HTTP=${p2.status}；toast="${p2toast}"；body=${J(p2.body, 200)}`, (p2.status === 422) ? '正常' : '缺陷', '');

      // 重新打标（覆盖）
      const t1P = waitResp(`/api/v1/assets/${upId}/tag`, 'POST', 180000);
      await page.click('button:has-text("重新打标（覆盖）")');
      let t1 = null; try { t1 = await (await t1P).json(); } catch (e) { t1 = { err: e.message.slice(0, 150) }; }
      await page.waitForTimeout(600);
      rec('素材详情', '「重新打标（覆盖）」', '点击覆盖打标', 'LLM 或规则兜底并标注来源', `tag_source=${t1 && t1.tag_source}；tags=${J(t1 && t1.tags)}；latency=${t1 && t1.meta && t1.meta.latency_ms}；degraded=${t1 && t1.degraded_reason || '-'}`, (t1 && t1.tag_source) ? (t1.tag_source === 'llm' ? '正常' : '部分') : '缺陷', await shot(page, 'asset-retag'));

      // 追加
      const t2P = waitResp(`/api/v1/assets/${upId}/tag`, 'POST', 180000);
      await page.click('button:has-text("追加")');
      let t2 = null; try { t2 = await (await t2P).json(); } catch (e) { t2 = { err: e.message.slice(0, 150) }; }
      rec('素材详情', '「追加」打标', '点击追加', '标签合并', `tag_source=${t2 && t2.tag_source}；tags=${J(t2 && t2.tags)}`, (t2 && t2.tags) ? '正常' : '缺陷', '');

      // 删除（含确认弹窗）
      lastDialog = null;
      const d1P = waitResp(`/api/v1/assets/${upId}`, 'DELETE', 60000);
      await page.click(`button:has-text("删除 ${upId}")`);
      let d1 = null; try { const r = await d1P; d1 = { status: r.status(), body: await r.json().catch(() => null) }; } catch (e) { d1 = { err: e.message.slice(0, 150) }; }
      await page.waitForTimeout(800);
      const afterDel = await page.evaluate(id => ({ inLibrary: document.body.innerText.includes(id) }), upId);
      rec('素材详情', `「删除 ${upId}」`, '点击删除（确认弹窗自动确认）', 'DELETE 200，文件一并删除，列表消失', `dialog="${lastDialog}"；HTTP=${d1.status}；file_removed=${d1.body && d1.body.file_removed}；删除后页面仍含ID=${afterDel.inLibrary}；body=${J(d1.body, 200)}`, (d1.status === 200) ? '正常' : '缺陷', await shot(page, 'asset-deleted'));
    } else {
      rec('素材详情', '深链打开', '-', '-', '上传未拿到 asset_id，跳过详情链路', '未测', '');
    }

    /* ── 6. 删除生成的规格卡；核对 LLM 网关累计调用 ───────── */
    if (genId) {
      await page.evaluate(id => { location.hash = 'asset/' + id; }, genId);
      await page.waitForFunction(() => document.body.innerText.includes('素材信息'), null, { timeout: 30000 });
      await page.waitForTimeout(500);
      const ddP = waitResp(`/api/v1/assets/${genId}`, 'DELETE', 60000);
      await page.click(`button:has-text("删除 ${genId}")`);
      let dd = null; try { const r = await ddP; dd = { status: r.status(), body: await r.json().catch(() => null) }; } catch (e) { dd = { err: e.message.slice(0, 120) }; }
      rec('素材详情', `清理生成的规格卡（${genId}）`, '删除', '删除成功', `HTTP=${dd.status}；file_removed=${dd.body && dd.body.file_removed}`, dd.status === 200 ? '正常' : '部分', '');
    }
    const st2 = await page.evaluate(async () => { const r = await fetch('/api/v1/llm/status'); return await r.json(); }).catch(() => null);
    rec('概览', 'LLM 网关累计', '读取 /llm/status', '调用次数/Token 随真实调用增长', `configured=${st2 && st2.configured}；model=${st2 && st2.model}；cost=${J(st2 && st2.cost, 300)}`, (st2 && st2.cost && st2.cost.total_calls >= 1) ? '正常' : '部分', '');

  } catch (e) {
    rec('全局', '脚本异常', '-', '全部步骤完成', '异常中断: ' + e.message.slice(0, 300), '缺陷', '');
  }

  const result = { base: BASE, tag: TAG, started, finished: new Date().toISOString(), steps, consoleMsgs, netFails, apiDumps };
  fs.writeFileSync(path.join(EVID, `agent5-p07-${TAG}-results.json`), JSON.stringify(result, null, 2), 'utf-8');
  clearTimeout(watchdog);
  console.log('WROTE agent5-p07-' + TAG + '-results.json ; steps=' + steps.length + ' console=' + consoleMsgs.length + ' netFails=' + netFails.length + ' apiDumps=' + apiDumps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });