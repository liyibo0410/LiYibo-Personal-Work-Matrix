/* Agent5 · P06 数据中台 按钮全量点击测试（只测不改）
 * 运行: node agent5-p06-sweep.js   (workdir 需含 node_modules/playwright)
 * env: P06_BASE (默认公网), P06_TAG (默认 public)
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const EVID = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.P06_BASE || 'http://39.96.200.45:8090/p06/';
const TAG = process.env.P06_TAG || 'public';
const TMPDIR = 'C:\\Users\\23329\\AppData\\Local\\Temp\\opencode\\p06p07-sweep';

const started = new Date().toISOString();
const steps = [];
const consoleMsgs = [];
const netFails = [];
const apiDumps = [];
let shotN = 1;

// 看门狗：若 15 分钟未完成（例如截图偶发挂起），落盘部分结果并以码 2 退出
const watchdog = setTimeout(() => {
  try { fs.writeFileSync(path.join(EVID, `agent5-p06-${TAG}-partial.json`), JSON.stringify({ base: BASE, tag: TAG, note: 'watchdog dump', steps, consoleMsgs, netFails, apiDumps }, null, 2), 'utf-8'); } catch (e) { }
  console.error('WATCHDOG: partial results dumped, exiting');
  process.exit(2);
}, 900000);

function rec(pageName, widget, action, expected, actual, verdict, evidence) {
  steps.push({ ts: new Date().toISOString(), page: pageName, widget, action, expected, actual: String(actual).slice(0, 1500), verdict, evidence });
  console.log(`[${verdict}] ${pageName} | ${widget} | ${action} | ${String(actual).slice(0, 160)}`);
}

async function shot(page, desc, fullPage) {
  const name = `agent5-${String(shotN).padStart(2, '0')}-p06-${TAG}-${desc}.png`;
  shotN++;
  try { await page.screenshot({ path: path.join(EVID, name), fullPage: !!fullPage, timeout: 20000, animations: 'disabled' }); }
  catch (e) { console.log('screenshot fail', name, e.message); }
  return name;
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1560, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(60000);

  page.on('console', m => {
    if (m.type() === 'error' || m.type() === 'warning') consoleMsgs.push({ type: m.type(), text: m.text().slice(0, 500), url: (m.location() || {}).url || '' });
  });
  page.on('pageerror', e => consoleMsgs.push({ type: 'pageerror', text: String(e).slice(0, 500) }));
  page.on('requestfailed', r => netFails.push({ url: r.url().slice(0, 300), err: (r.failure() || {}).errorText || '' }));
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/api/v1/')) {
      let body = null;
      try { body = JSON.stringify(await r.json()).slice(0, 5000); } catch (e) { }
      apiDumps.push({ url: u.slice(0, 300), status: r.status(), body });
    }
  });

  try {
    /* ── 0. 首屏 ─────────────────────────────────────────── */
    const resp = await page.goto(BASE, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(2500);
    const dashState = await page.evaluate(() => ({
      title: document.title,
      badge: (document.getElementById('dash-badge') || {}).textContent || '',
      statCards: document.querySelectorAll('#dash-stats .stat-card').length,
      metricCards: [...document.querySelectorAll('#dash-metrics .stat-card')].map(c => c.innerText.replace(/\n/g, ' | ')),
      healthScore: (document.getElementById('health-ring') || {}).innerText || '',
      layers: (document.getElementById('dash-layers') || {}).innerText || '',
      navItems: [...document.querySelectorAll('.nav-item')].map(n => n.dataset.page),
      bodyBg: getComputedStyle(document.body).backgroundColor,
    }));
    rec('总览', '页面加载', `打开 ${BASE}`, '首屏正常渲染（HTTP 200）', `HTTP ${resp.status()}；badge="${dashState.badge}"；statCards=${dashState.statCards}；metricCards=${dashState.metricCards.length}；bg=${dashState.bodyBg}`,
      resp.status() === 200 && dashState.statCards === 4 && dashState.metricCards.length === 7 ? '正常' : '部分',
      await shot(page, 'dashboard'));
    rec('总览', '导航 Tab 枚举', '读取所有 nav-item', '总览/数据表/指标/质量/血缘/接入 6 个（无「查询」Tab）', JSON.stringify(dashState.navItems), dashState.navItems.length === 6 ? '正常' : '部分', 'DOM 快照');
    rec('总览', '指标卡（核心指标概览）', '读取 7 项指标卡文本', 'GMV/订单/转化率/客单价/退货率/UV/PV 齐全且有口径标注',
      JSON.stringify(dashState.metricCards), dashState.metricCards.length === 7 ? '部分' : '缺陷', '指标卡仅显示 名称/最新值/趋势，未显示口径说明（接口 metric.description 有口径但页面未展示）');
    rec('总览', '健康环/数仓分层', '读取文本', '健康分与分层显示', `${dashState.healthScore} / ${dashState.layers.replace(/\n/g, '; ')}`, '正常', '同截图');

    /* ── 1. 数据表管理 ───────────────────────────────────── */
    await page.click('.nav-item[data-page="tables"]');
    await page.waitForFunction(() => document.querySelectorAll('#tables-table tbody tr').length >= 5, null, { timeout: 30000 });
    const tableRows = await page.$$eval('#tables-table tbody tr', trs => trs.map(tr => tr.querySelector('td').innerText));
    const shotTables = await shot(page, 'tables-list');
    rec('数据表', '进入 Tab', '点击侧栏「数据表管理」', '加载表列表', `${tableRows.length} 张表: ${tableRows.join(',')}`, tableRows.length >= 5 ? '正常' : '缺陷', shotTables);

    // 分层筛选
    for (const layer of ['ODS', 'DWD', 'DWS', 'ADS', '']) {
      await page.selectOption('#table-layer-filter', layer);
      await page.waitForTimeout(300);
      const n = await page.$$eval('#tables-table tbody tr', trs => trs.length);
      const layersShown = await page.$$eval('#tables-table tbody tr td:nth-child(3)', tds => [...new Set(tds.map(t => t.innerText))]);
      rec('数据表', '分层筛选 select', `选择 ${layer || '全部'}`, '仅显示对应分层（或全部）', `行数=${n}，分层=${layersShown.join('/')}`, (layer === '' || (layersShown.length === 1 && layersShown[0] === layer)) ? '正常' : '缺陷', layer === 'ODS' ? await shot(page, 'tables-filter-ods') : '');
    }

    // 每行的「查看」按钮 → 详情 → 「关闭」（失败重试一次；超时压到 9s，避免多轮等待拖过看门狗）
    const rowCount = await page.$$eval('#tables-table tbody tr', trs => trs.length);
    let detailOk = 0; const detailFail = [];
    for (let i = 1; i <= rowCount; i++) {
      const tname = await page.$eval(`#tables-table tbody tr:nth-child(${i}) td`, td => td.innerText);
      let opened = false, errLog = '';
      for (let attempt = 1; attempt <= 2 && !opened; attempt++) {
        const dumpIdx = apiDumps.length;
        try {
          await page.click(`#tables-table tbody tr:nth-child(${i}) button`);
          await page.waitForFunction(() => {
            const d = document.getElementById('table-detail');
            return d && d.style.display !== 'none' && document.querySelectorAll('#detail-preview-body tr').length > 0;
          }, null, { timeout: 9000 });
          opened = true;
          detailOk++;
          const title = await page.$eval('#detail-title', el => el.innerText);
          const cols = await page.$$eval('#detail-columns tbody tr', trs => trs.length);
          const preview = await page.$$eval('#detail-preview-body tr', trs => trs.length);
          rec('数据表', `「查看」 ${tname}`, `点击第 ${i} 行「查看」`, '详情面板+预览', `打开成功（第${attempt}次）："${title}" 列=${cols} 预览行=${preview}`, '正常', i === 1 ? await shot(page, 'table-detail-first') : '');
          await page.click('#table-detail button'); // 关闭
          await page.waitForFunction(() => document.getElementById('table-detail').style.display === 'none', null, { timeout: 6000 });
        } catch (e) {
          errLog += `attempt${attempt}:${e.message.split('\n')[0]} `;
          const related = apiDumps.slice(dumpIdx).filter(d => d.url.includes('/tables/' + tname)).map(d => `${d.status} ${d.url.split('/api/v1/')[1]}`);
          errLog += related.length ? `[api: ${related.join('; ')}] ` : '[no api call captured] ';
          try { await page.click('#table-detail button'); await page.waitForFunction(() => document.getElementById('table-detail').style.display === 'none', null, { timeout: 4000 }); } catch (e2) { }
        }
      }
      if (!opened) {
        detailFail.push(tname);
        rec('数据表', `「查看」 ${tname}`, `点击第 ${i} 行「查看」`, '详情面板+预览', `两次均失败：${errLog}`, '缺陷', '');
      }
    }
    rec('数据表', `「查看」按钮汇总 × ${rowCount}`, '逐一点击并关闭', '每张表都能打开详情并关闭', `成功 ${detailOk}/${rowCount}；失败 ${detailFail.length} 张: ${detailFail.join(', ')}`, detailFail.length === 0 ? '正常' : '缺陷', '遍历测试（失败项含重试与相关接口状态）');

    /* ── 2. 指标探查 ─────────────────────────────────────── */
    await page.click('.nav-item[data-page="metrics"]');
    await page.waitForFunction(() => document.querySelectorAll('#metric-code option').length >= 7, null, { timeout: 30000 });
    const metricOpts = await page.$$eval('#metric-code option', os => os.map(o => o.textContent.trim()));
    rec('指标', '进入 Tab', '点击侧栏「指标探查」', '指标下拉含 7 项', `${metricOpts.length} 项: ${metricOpts.join(' / ')}`, metricOpts.length === 7 ? '正常' : '缺陷', 'DOM');

    const codes = ['gmv', 'order_count', 'conversion_rate', 'avg_order_value', 'return_rate', 'traffic_uv', 'traffic_pv'];
    const granMap = { gmv: 'day', return_rate: 'week', traffic_pv: 'month' };
    let chartOk = 0, chartFail = [];
    for (const code of codes) {
      try {
        await page.selectOption('#metric-code', code);
        if (granMap[code]) await page.selectOption('#metric-granularity', granMap[code]);
        const respP = page.waitForResponse(r => r.url().includes(`/api/v1/metrics/${code}/query`), { timeout: 30000 });
        const t0 = Date.now();
        await page.click('button:has-text("查询")');
        const r = await respP;
        await page.waitForFunction(() => document.querySelectorAll('#metric-summary .stat-card').length === 4, null, { timeout: 15000 });
        const summary = await page.$$eval('#metric-summary .stat-card', cs => cs.map(c => c.innerText.replace(/\n/g, '=')));
        // echarts 为懒加载（1MB 经公网隧道），首查可能晚到 — 最多等 45s
        try { await page.waitForFunction(() => document.querySelectorAll('#metric-chart canvas').length > 0, null, { timeout: 45000 }); } catch (e) { }
        const canvas = await page.$eval('#metric-chart', el => el.querySelectorAll('canvas').length);
        const chartMs = Date.now() - t0;
        chartOk++;
        rec('指标', `查询按钮（${code}）`, `选择指标=${code}, 粒度=${granMap[code] || 'day'}，点击「查询」`, '摘要卡更新 + 图表渲染', `HTTP ${r.status()}；摘要=${summary.join(' | ')}；canvas=${canvas}；出图耗时≈${chartMs}ms`, (r.status() === 200 && canvas > 0) ? '正常' : '缺陷', code === 'gmv' ? await shot(page, 'metrics-gmv') : (code === 'traffic_pv' ? await shot(page, 'metrics-pv-month') : ''));
      } catch (e) {
        chartFail.push(`${code}: ${e.message.slice(0, 160)}`);
      }
    }
    rec('指标', '7 项指标逐一查询', '遍历 gmv/order_count/conversion_rate/avg_order_value/return_rate/traffic_uv/traffic_pv', '7 项全部可查询且出图', `成功 ${chartOk}/7${chartFail.length ? '；失败: ' + chartFail.join(' || ') : ''}`, chartFail.length === 0 ? '正常' : '缺陷', '遍历测试');

    /* ── 3. 数据质量 ─────────────────────────────────────── */
    await page.click('.nav-item[data-page="quality"]');
    await page.waitForTimeout(500);
    const qRespP = page.waitForResponse(r => r.url().includes('/api/v1/quality/check'), { timeout: 60000 });
    await page.click('button:has-text("运行质量检查")');
    let qRespStatus = -1;
    try { qRespStatus = (await qRespP).status(); } catch (e) { }
    try { await page.waitForFunction(() => document.getElementById('quality-status').textContent.includes('检查完成'), null, { timeout: 60000 }); } catch (e) { }
    const q = await page.evaluate(() => ({
      status: document.getElementById('quality-status').textContent,
      summary: [...document.querySelectorAll('#quality-summary .stat-card')].map(c => c.innerText.replace(/\n/g, '=')),
      rows: document.querySelectorAll('#quality-table tbody tr').length,
      firstRows: [...document.querySelectorAll('#quality-table tbody tr')].slice(0, 3).map(tr => tr.innerText.replace(/\n/g, ' | ')),
      toast: document.getElementById('toast-container').innerText.replace(/\n/g, ' ; '),
    }));
    rec('质量', '「运行质量检查」按钮', '点击运行', '状态=检查完成，汇总卡与明细更新', `HTTP ${qRespStatus}；status="${q.status}"；汇总=${q.summary.join(' | ')}；明细行=${q.rows}；toast=${q.toast}`, (q.rows > 0 && q.status.includes('检查完成')) ? '正常' : '缺陷', await shot(page, 'quality-results'));

    /* ── 4. 数据血缘 ─────────────────────────────────────── */
    await page.click('.nav-item[data-page="lineage"]');
    await page.waitForFunction(() => document.querySelectorAll('#lineage-svg rect').length > 0, null, { timeout: 30000 }).catch(() => { });
    await page.waitForTimeout(800);
    const lin = await page.evaluate(() => ({
      nodes: document.querySelectorAll('#lineage-svg rect').length,
      edges: document.querySelectorAll('#lineage-svg path').length,
      texts: [...document.querySelectorAll('#lineage-svg text')].map(t => t.textContent).slice(0, 20),
      tableRows: document.querySelectorAll('#lineage-table tbody tr').length,
      svgBox: document.getElementById('lineage-svg').getBoundingClientRect().height,
    }));
    rec('血缘', '进入 Tab', '点击侧栏「数据血缘」', '渲染出图谱（节点+连线+明细表）', `节点rect=${lin.nodes}，连线path=${lin.edges}，SVG高=${Math.round(lin.svgBox)}，明细行=${lin.tableRows}；节点文本=${lin.texts.slice(0, 10).join(',')}`, (lin.nodes > 0 && lin.edges > 0 && lin.tableRows > 0) ? '正常' : '缺陷', await shot(page, 'lineage', true));
    const linInteractive = await page.evaluate(() => {
      const g = document.querySelector('#lineage-svg g');
      return g ? (g.getAttribute('onclick') || window.getComputedStyle(g).cursor) : 'no-g';
    });
    rec('血缘', '图可交互性', '检查节点是否有点击/悬停交互', '现状为静态渲染（只读展示）', `首节点 cursor/onclick = ${linInteractive}`, '正常', '无 click 处理器 — 静态图，非缺陷但注明');

    /* ── 5. 数据接入（上传 CSV/JSON + 非法表名拒绝） ───────── */
    const csvPath = path.join(TMPDIR, 'tmp_uitest_agent5.csv');
    const jsonPath = path.join(TMPDIR, 'tmp_uitest_agent5.json');
    fs.writeFileSync(csvPath, 'campaign,impressions,clicks,cost\nui_test_banner,1000,55,120.5\nui_test_video,2000,80,300.0\nui_test_post,800,20,50.0\n', 'utf-8');
    fs.writeFileSync(jsonPath, JSON.stringify([
      { sku: 'UI-TEST-1', name: '测试商品A', price: 19.9, qty: 3 },
      { sku: 'UI-TEST-2', name: '测试商品B', price: 29.9, qty: 1 },
      { sku: 'UI-TEST-3', name: '测试商品C', price: 9.9, qty: 10 },
    ]), 'utf-8');

    await page.click('.nav-item[data-page="ingest"]');
    await page.waitForTimeout(400);
    rec('接入', '进入 Tab', '点击侧栏「数据接入」', '显示 CSV/JSON 上传区与日志', (await page.$eval('#ingest-log', el => el.innerText)).slice(0, 60), '正常', await shot(page, 'ingest-initial'));

    // 拖拽区点击 → 文件选择器
    try {
      const [fc] = await Promise.all([
        page.waitForEvent('filechooser', { timeout: 10000 }),
        page.click('#csv-zone'),
      ]);
      await fc.setFiles([]).catch(() => { });
      rec('接入', 'CSV 拖拽区点击', '点击上传区', '弹出文件选择器', 'filechooser 事件触发', '正常', '未实际上传');
    } catch (e) {
      rec('接入', 'CSV 拖拽区点击', '点击上传区', '弹出文件选择器', 'filechooser 未触发: ' + e.message.split('\n')[0], '缺陷', '');
    }

    // CSV 上传
    await page.fill('#csv-table', 'tmp_uitest_agent5_csv');
    await page.selectOption('#csv-layer', 'ODS');
    await page.setInputFiles('#csv-input', csvPath);
    let csvLog = '';
    try {
      await page.waitForFunction(() => document.getElementById('ingest-log').textContent.includes('成功'), null, { timeout: 30000 });
      csvLog = await page.$eval('#ingest-log', el => el.innerText);
    } catch (e) { csvLog = await page.$eval('#ingest-log', el => el.innerText); }
    rec('接入', 'CSV 上传（tmp_uitest_agent5_csv）', '填表名+选层+选择CSV文件', '上传成功并显示行数/列数', csvLog.split('\n').slice(-3).join(' || '), csvLog.includes('成功') ? '正常' : '缺陷', await shot(page, 'ingest-csv-done'));

    // JSON 上传
    await page.fill('#json-table', 'tmp_uitest_agent5_json');
    await page.selectOption('#json-layer', 'DWD');
    await page.setInputFiles('#json-input', jsonPath);
    let jsonLog = '';
    try {
      await page.waitForFunction(() => (document.getElementById('ingest-log').textContent.match(/成功/g) || []).length >= 2, null, { timeout: 30000 });
      jsonLog = await page.$eval('#ingest-log', el => el.innerText);
    } catch (e) { jsonLog = await page.$eval('#ingest-log', el => el.innerText); }
    rec('接入', 'JSON 上传（tmp_uitest_agent5_json）', '填表名+选层+选择JSON文件', '上传成功并显示行数/列数', jsonLog.split('\n').slice(-3).join(' || '), jsonLog.includes('成功') ? '正常' : '缺陷', await shot(page, 'ingest-json-done'));

    // 非法表名 → 应被拒绝
    await page.fill('#json-table', 'tmp_uitest_bad name!');
    await page.setInputFiles('#json-input', jsonPath);
    let badLog = '';
    try {
      await page.waitForFunction(() => document.getElementById('ingest-log').textContent.includes('失败'), null, { timeout: 30000 });
    } catch (e) { }
    badLog = await page.$eval('#ingest-log', el => el.innerText);
    const badToast = await page.$eval('#toast-container', el => el.innerText).catch(() => '');
    rec('接入', '非法表名拒绝（tmp_uitest_bad name!）', '表名含空格/感叹号上传', '被护栏拒绝并给出明确说明', `log尾: ${badLog.split('\n').slice(-2).join(' || ')}；toast: ${badToast}`, badLog.includes('非法表名') ? '正常' : '缺陷', await shot(page, 'ingest-invalid-rejected'));

    // 回到数据表确认两张临时表存在（DOM 列 + API 双重核对）
    await page.click('.nav-item[data-page="tables"]');
    await page.waitForFunction(() => document.querySelectorAll('#tables-table tbody tr').length >= 5, null, { timeout: 30000 });
    const tmpVisible = await page.evaluate(() => {
      const names = [...document.querySelectorAll('#tables-table tbody tr td:first-child')].map(td => td.innerText.trim());
      return {
        hasCsv: names.includes('tmp_uitest_agent5_csv'),
        hasJson: names.includes('tmp_uitest_agent5_json'),
        hasBad: names.some(n => n.includes('tmp_uitest_bad')),
        totalRows: names.length,
      };
    });
    const apiTmp = await page.evaluate(async () => {
      const r = await fetch('/api/v1/tables'); const j = await r.json();
      const names = (j.data || []).map(t => t.table_name);
      return { hasCsv: names.includes('tmp_uitest_agent5_csv'), hasJson: names.includes('tmp_uitest_agent5_json'), hasBad: names.some(n => n.includes('tmp_uitest_bad')), total: names.length };
    });
    rec('数据表', '临时表可见性', '上传后回表列表查看（DOM + API 双核对）', '两张 tmp 表在列，非法名未建表', `DOM: ${JSON.stringify(tmpVisible)} / API: ${JSON.stringify(apiTmp)}`, (tmpVisible.hasCsv && tmpVisible.hasJson && !apiTmp.hasBad) ? '正常' : '缺陷', await shot(page, 'tables-tmp-visible'));

    /* ── 6. SQL 查询接口（无 UI 入口，直接调接口） ─────────── */
    async function postQuery(sql) {
      return await page.evaluate(async (s) => {
        const res = await fetch('/api/v1/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql: s }) });
        let j = null; try { j = await res.json(); } catch (e) { }
        return { status: res.status, code: j && j.code, msg: j && j.msg, sample: j && j.data ? JSON.stringify(j.data).slice(0, 300) : null };
      }, sql);
    }
    const legal = await postQuery('SELECT COUNT(*) AS cnt, ROUND(SUM(gmv),2) AS gmv FROM ads_key_metrics');
    rec('查询(API)', '合法 SELECT', 'POST /api/v1/query 跑 SELECT COUNT/SUM', '返回结果集', JSON.stringify(legal), (legal.status === 200 && legal.code === 0) ? '正常' : '缺陷', '无 UI 入口，接口直调（页面无「查询」Tab）');

    const guard1 = await postQuery('SELECT 1; DROP TABLE tmp_uitest_guard_probe');
    rec('查询(API)', '护栏-多语句夹带 DROP', 'POST /api/v1/query 载荷 "SELECT 1; DROP TABLE tmp_uitest_guard_probe"', '被拦截且说明清楚', JSON.stringify(guard1), (guard1.code === 1 && /多条语句|不允许多条/.test(guard1.msg || '')) ? '正常' : '缺陷', '无害载荷');

    const guard2 = await postQuery("SELECT * FROM read_text('.env')");
    rec('查询(API)', '护栏-读文件函数', "POST /api/v1/query 载荷 SELECT * FROM read_text('.env')", '被拦截', JSON.stringify(guard2), (guard2.code === 1) ? '正常' : '缺陷', '无害载荷');

    const probeCheck = await page.evaluate(async () => {
      const r = await fetch('/api/v1/tables'); const j = await r.json();
      const names = (j.data || []).map(t => t.table_name);
      return { hasProbe: names.includes('tmp_uitest_guard_probe'), total: names.length };
    });
    rec('查询(API)', '确认未建表', 'GET /api/v1/tables 检查 tmp_uitest_guard_probe', '载荷未实际建表/删表', JSON.stringify(probeCheck), probeCheck.hasProbe === false ? '正常' : '缺陷(数据被破坏)', '护栏验证');

    /* ── 7. 上传区点击（文件选择器）已在上方接入 Tab 内完成 ── */

  } catch (e) {
    rec('全局', '脚本异常', '-', '全部步骤完成', '异常中断: ' + e.message.slice(0, 300), '缺陷', '');
  }

  const result = {
    base: BASE, tag: TAG, started, finished: new Date().toISOString(),
    steps, consoleMsgs, netFails, apiDumps,
  };
  fs.writeFileSync(path.join(EVID, `agent5-p06-${TAG}-results.json`), JSON.stringify(result, null, 2), 'utf-8');
  clearTimeout(watchdog);
  console.log('WROTE agent5-p06-' + TAG + '-results.json ; steps=' + steps.length + ' console=' + consoleMsgs.length + ' netFails=' + netFails.length + ' apiDumps=' + apiDumps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });