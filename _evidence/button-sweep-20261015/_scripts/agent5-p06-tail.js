/* Agent5 · P06 本地补尾：指标/质量/血缘/接入(含 filechooser)/SQL 护栏/查看循环(修超时)/tmp 核对
 * 独立 JSON: agent5-p06-local-tail-results.json（看门狗超时则写 *-tail-partial.json）
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const EVID = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.T_BASE || 'http://127.0.0.1:8060/';
const TMPDIR = 'C:\\Users\\23329\\AppData\\Local\\Temp\\opencode\\p06p07-sweep';

const steps = [], consoleMsgs = [], netFails = [], apiDumps = [];
let shotN = 30;
function rec(pageName, widget, action, expected, actual, verdict, evidence) {
  steps.push({ ts: new Date().toISOString(), page: pageName, widget, action, expected, actual: String(actual).slice(0, 1500), verdict, evidence });
  console.log(`[${verdict}] ${pageName} | ${widget} | ${String(actual).slice(0, 150)}`);
}
async function shot(page, desc, fullPage) {
  const name = `agent5-${String(shotN++).padStart(2, '0')}-p06-tail-${desc}.png`;
  try { await page.screenshot({ path: path.join(EVID, name), fullPage: !!fullPage, timeout: 20000, animations: 'disabled' }); } catch (e) { console.log('shot fail', e.message); }
  return name;
}
const watchdog = setTimeout(() => {
  try { fs.writeFileSync(path.join(EVID, 'agent5-p06-local-tail-partial.json'), JSON.stringify({ base: BASE, steps, consoleMsgs, netFails, apiDumps }, null, 2), 'utf-8'); } catch (e) { }
  console.error('TAIL WATCHDOG: partial dumped'); process.exit(2);
}, 780000);

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1560, height: 950 }, locale: 'zh-CN' })).newPage();
  page.setDefaultTimeout(20000);
  page.setDefaultNavigationTimeout(60000);
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') consoleMsgs.push({ type: m.type(), text: m.text().slice(0, 300) }); });
  page.on('pageerror', e => consoleMsgs.push({ type: 'pageerror', text: String(e).slice(0, 300) }));
  page.on('requestfailed', r => netFails.push({ url: r.url().slice(0, 200), err: (r.failure() || {}).errorText || '' }));
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/api/v1/')) { let b = null; try { b = JSON.stringify(await r.json()).slice(0, 4000); } catch (e) { } apiDumps.push({ url: u.slice(0, 220), status: r.status(), body: b }); }
  });
  const waitResp = (part, method, t) => page.waitForResponse(r => r.url().includes(part) && (!method || r.request().method() === method), { timeout: t || 40000 });

  try {
    await page.goto(BASE, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(2000);

    /* 指标：7 项 + 出图耗时 */
    await page.click('.nav-item[data-page="metrics"]');
    await page.waitForFunction(() => document.querySelectorAll('#metric-code option').length >= 7, null, { timeout: 30000 });
    const codes = ['gmv', 'order_count', 'conversion_rate', 'avg_order_value', 'return_rate', 'traffic_uv', 'traffic_pv'];
    let ok = 0; const timings = [];
    for (const code of codes) {
      const t0 = Date.now();
      try {
        await page.selectOption('#metric-code', code);
        const rp = waitResp(`/api/v1/metrics/${code}/query`, 'GET');
        await page.click('button:has-text("查询")');
        const r = await rp;
        let canvas = 0;
        try { await page.waitForFunction(() => document.querySelectorAll('#metric-chart canvas').length > 0, null, { timeout: 30000 }); } catch (e) { }
        canvas = await page.$eval('#metric-chart', el => el.querySelectorAll('canvas').length);
        ok++;
        timings.push(`${code}:${Date.now() - t0}ms/canvas=${canvas}`);
      } catch (e) { timings.push(`${code}:FAIL(${e.message.split('\n')[0].slice(0, 60)})`); }
    }
    rec('指标', '查询按钮 ×7（本地补尾）', '逐一查询 7 指标并等出图', '7/7 出数出图', `成功 ${ok}/7；单项耗时: ${timings.join(' | ')}`, ok === 7 ? '正常' : '缺陷', await shot(page, 'metrics-final'));

    /* 质量 */
    await page.click('.nav-item[data-page="quality"]');
    await page.waitForTimeout(400);
    const qP = waitResp('/api/v1/quality/check', 'GET', 60000);
    await page.click('button:has-text("运行质量检查")');
    let qStatus = -1; try { qStatus = (await qP).status(); } catch (e) { }
    try { await page.waitForFunction(() => document.getElementById('quality-status').textContent.includes('检查完成'), null, { timeout: 60000 }); } catch (e) { }
    const q = await page.evaluate(() => ({ s: document.getElementById('quality-status').textContent, sum: [...document.querySelectorAll('#quality-summary .stat-card')].map(c => c.innerText.replace(/\n/g, '=')), rows: document.querySelectorAll('#quality-table tbody tr').length }));
    rec('质量', '运行质量检查（本地补尾）', '点击运行', '检查完成+汇总+明细', `HTTP ${qStatus}；"${q.s}"；${q.sum.join(' | ')}；明细=${q.rows}`, q.rows > 0 ? '正常' : '缺陷', await shot(page, 'quality'));

    /* 血缘 */
    await page.click('.nav-item[data-page="lineage"]');
    await page.waitForFunction(() => document.querySelectorAll('#lineage-svg rect').length > 0, null, { timeout: 30000 }).catch(() => { });
    await page.waitForTimeout(600);
    const lin = await page.evaluate(() => ({ n: document.querySelectorAll('#lineage-svg rect').length, e: document.querySelectorAll('#lineage-svg path').length, rows: document.querySelectorAll('#lineage-table tbody tr').length, h: Math.round(document.getElementById('lineage-svg').getBoundingClientRect().height) }));
    rec('血缘', '进入 Tab（本地补尾）', '渲染检查', '图谱+明细', `节点=${lin.n}，连线=${lin.e}，SVG高=${lin.h}，明细=${lin.rows}`, (lin.n > 0 && lin.e > 0) ? '正常' : '缺陷', await shot(page, 'lineage', true));

    /* 接入 */
    const csvPath = path.join(TMPDIR, 'tmp_uitest_agent5.csv');
    const jsonPath = path.join(TMPDIR, 'tmp_uitest_agent5.json');
    await page.click('.nav-item[data-page="ingest"]');
    await page.waitForTimeout(400);
    // filechooser
    try {
      const [fc] = await Promise.all([page.waitForEvent('filechooser', { timeout: 10000 }), page.click('#csv-zone')]);
      await fc.setFiles([]).catch(() => { });
      rec('接入', 'CSV 拖拽区点击（本地补尾）', '点击上传区', '弹文件选择器', 'filechooser 触发', '正常', '');
    } catch (e) { rec('接入', 'CSV 拖拽区点击（本地补尾）', '点击上传区', '弹文件选择器', '未触发: ' + e.message.split('\n')[0], '缺陷', ''); }
    // 上传
    await page.fill('#csv-table', 'tmp_uitest_agent5_csv');
    await page.setInputFiles('#csv-input', csvPath);
    try { await page.waitForFunction(() => document.getElementById('ingest-log').textContent.includes('成功'), null, { timeout: 30000 }); } catch (e) { }
    const csvLog = await page.$eval('#ingest-log', el => el.innerText);
    rec('接入', 'CSV 上传（本地补尾，重跑替换同名 tmp 表）', '同名重传', '成功', csvLog.split('\n').slice(-1)[0], csvLog.includes('成功') ? '正常' : '缺陷', await shot(page, 'ingest-csv'));
    await page.fill('#json-table', 'tmp_uitest_agent5_json');
    await page.setInputFiles('#json-input', jsonPath);
    try { await page.waitForFunction(() => (document.getElementById('ingest-log').textContent.match(/成功/g) || []).length >= 2, null, { timeout: 30000 }); } catch (e) { }
    const jsonLog = await page.$eval('#ingest-log', el => el.innerText);
    rec('接入', 'JSON 上传（本地补尾）', '同名重传', '成功', jsonLog.split('\n').slice(-1)[0], jsonLog.includes('成功') ? '正常' : '缺陷', await shot(page, 'ingest-json'));
    await page.fill('#json-table', 'tmp_uitest_bad name!');
    await page.setInputFiles('#json-input', jsonPath);
    try { await page.waitForFunction(() => document.getElementById('ingest-log').textContent.includes('失败'), null, { timeout: 30000 }); } catch (e) { }
    const badLog = await page.$eval('#ingest-log', el => el.innerText);
    rec('接入', '非法表名（本地补尾复核）', 'tmp_uitest_bad name!', '拒绝', badLog.split('\n').slice(-1)[0].slice(0, 200), badLog.includes('非法表名') ? '正常' : '缺陷', '');

    /* SQL 护栏（本地复验） */
    const post = (sql) => page.evaluate(async s => { const r = await fetch('/api/v1/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql: s }) }); const j = await r.json().catch(() => null); return { status: r.status, code: j && j.code, msg: j && j.msg }; }, sql);
    const l1 = await post('SELECT COUNT(*) AS cnt, ROUND(SUM(gmv),2) AS gmv FROM ads_key_metrics');
    rec('查询(API)', '合法 SELECT（本地复验）', 'COUNT/SUM 查询', '返回结果', JSON.stringify(l1), l1.code === 0 ? '正常' : '缺陷', '');
    const l2 = await post('SELECT 1; DROP TABLE tmp_uitest_guard_probe');
    rec('查询(API)', '护栏-多语句（本地复验）', '无害载荷', '拦截', JSON.stringify(l2), l2.code === 1 ? '正常' : '缺陷', '');
    const l3 = await post("SELECT * FROM read_text('.env')");
    rec('查询(API)', '护栏-read_text（本地复验）', '无害载荷', '拦截', JSON.stringify(l3), l3.code === 1 ? '正常' : '缺陷', '');
    const l4 = await page.evaluate(async () => { const r = await fetch('/api/v1/tables'); const j = await r.json(); return (j.data || []).some(t => t.table_name === 'tmp_uitest_guard_probe'); });
    rec('查询(API)', '未建表复核（本地复验）', '探针表不应存在', '不存在', String(l4), l4 === false ? '正常' : '缺陷', '');

    /* 数据表：查看循环（修短超时）+ tmp 核对 */
    await page.click('.nav-item[data-page="tables"]');
    await page.waitForFunction(() => document.querySelectorAll('#tables-table tbody tr').length >= 5, null, { timeout: 30000 });
    const rowCount = await page.$$eval('#tables-table tbody tr', trs => trs.length);
    let viewOk = 0; const viewFail = [];
    for (let i = 1; i <= rowCount; i++) {
      const tname = await page.$eval(`#tables-table tbody tr:nth-child(${i}) td`, td => td.innerText);
      let opened = false, err = '';
      for (let attempt = 1; attempt <= 2 && !opened; attempt++) {
        const dIdx = apiDumps.length;
        try {
          await page.click(`#tables-table tbody tr:nth-child(${i}) button`);
          await page.waitForFunction(() => { const d = document.getElementById('table-detail'); return d && d.style.display !== 'none' && document.querySelectorAll('#detail-preview-body tr').length > 0; }, null, { timeout: 9000 });
          opened = true; viewOk++;
          await page.click('#table-detail button', { timeout: 4000 });
          await page.waitForFunction(() => document.getElementById('table-detail').style.display === 'none', null, { timeout: 4000 }).catch(() => { });
        } catch (e) {
          err += `A${attempt}[${e.message.split('\n')[0].slice(0, 50)}; ${apiDumps.slice(dIdx).filter(d => d.url.includes('/tables/' + tname)).map(d => d.status).join('/')}] `;
          await page.click('#table-detail button', { timeout: 1500 }).catch(() => { });
          await page.waitForTimeout(300);
        }
      }
      if (!opened) rec('数据表', `「查看」${tname}（补尾）`, '点击2次重试', '详情打开', `失败: ${err}`, '缺陷', '');
    }
    rec('数据表', `「查看」循环汇总（本地补尾）×${rowCount}`, '逐行点击', '全部打开', `成功 ${viewOk}/${rowCount}；失败 ${viewFail.length || (rowCount - viewOk)} 张`, viewOk === rowCount ? '正常' : '缺陷', '');
    const tmp = await page.evaluate(async () => {
      const names = [...document.querySelectorAll('#tables-table tbody tr td:first-child')].map(td => td.innerText.trim());
      const r = await fetch('/api/v1/tables'); const j = await r.json();
      const api = (j.data || []).map(t => t.table_name);
      return { domCsv: names.includes('tmp_uitest_agent5_csv'), domJson: names.includes('tmp_uitest_agent5_json'), domBad: names.some(n => n.includes('tmp_uitest_bad')), apiCsv: api.includes('tmp_uitest_agent5_csv'), apiJson: api.includes('tmp_uitest_agent5_json'), apiBad: api.some(n => n.includes('tmp_uitest_bad')), total: api.length };
    });
    rec('数据表', 'tmp 可见性（本地补尾核对）', 'DOM+API', '两 tmp 在、非法名无', JSON.stringify(tmp), (tmp.domCsv && tmp.domJson && tmp.apiCsv && tmp.apiJson && !tmp.apiBad) ? '正常' : '缺陷', await shot(page, 'tables-tmp'));

  } catch (e) { rec('全局', '补尾脚本异常', '-', '完成', '异常中断: ' + e.message.slice(0, 200), '缺陷', ''); }

  fs.writeFileSync(path.join(EVID, 'agent5-p06-local-tail-results.json'), JSON.stringify({ base: BASE, ts: new Date().toISOString(), steps, consoleMsgs, netFails, apiDumps }, null, 2), 'utf-8');
  clearTimeout(watchdog);
  console.log('TAIL WROTE ; steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });