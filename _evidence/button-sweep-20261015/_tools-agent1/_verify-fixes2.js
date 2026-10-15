/* 监督窗口验证脚本 v3（只读）：P09/P10/P06 前端函数可见性 + 页面错误
 * 用法（在 _tools-agent1 目录下，含 playwright 依赖）：
 *   node _verify-fixes2.js
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const out = { ts: new Date().toISOString() };
  const pages = [
    ['p10', 'http://127.0.0.1:8101/', ['pullFromP09', 'loadTraining', 'startTraining', 'loadDatasets']],
    ['p09', 'http://127.0.0.1:8090/', ['importFromP01', 'runEvaluate', 'exportLowScore', 'loadDashboard']],
    ['p06', 'http://127.0.0.1:8060/', ['queryMetric', 'renderMetricChart', 'ensureEcharts']],
  ];
  for (const [name, url, fns] of pages) {
    const p = await browser.newPage();
    const errs = [];
    p.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
    p.on('console', (m) => { if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 140)); });
    await p.goto(url, { waitUntil: 'load', timeout: 30000 }).catch((e) => errs.push('goto ' + e.message));
    await p.waitForTimeout(2500);
    out[name] = {
      fns: await p.evaluate((list) => Object.fromEntries(list.map((f) => [f, typeof window[f]])), fns),
      errors: errs.slice(0, 6),
    };
    await p.close();
  }
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});