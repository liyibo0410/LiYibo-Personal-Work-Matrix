/* 监督窗口复现：2.8 P02 aria-current 水合告警 —— 捕获 React 原文警告 + 落地后的 aria-current 快照 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await browser.newPage();
  const hits = [];
  p.on('console', (m) => {
    const t = m.text();
    if (/did not match|hydration|hydrat/i.test(t)) hits.push({ type: m.type(), text: t.slice(0, 400) });
  });
  p.on('pageerror', (e) => hits.push({ type: 'pageerror', text: String(e.message).slice(0, 300) }));

  await p.goto('http://127.0.0.1:3001/login', { waitUntil: 'load', timeout: 40000 }).catch((e) => hits.push({ type: 'goto', text: e.message }));
  await p.waitForTimeout(2500);
  await p.fill('input[type="email"]', 'boss@example.com').catch(() => {});
  await p.fill('input[type="password"]', 'Test123456').catch(() => {});
  await p.click('button[type="submit"]').catch(() => {});
  await p.waitForTimeout(4000);
  // 关键：agent3 的场景是**整页加载**（SSR + 水合）且 URL 带 ?cp-theme=light（外壳挂载
  // URL 一律带它，日志里告警也全部跟着该参数出现）；登录后的客户端导航不触发水合
  await p.goto('http://127.0.0.1:3001/?cp-theme=light', { waitUntil: 'load', timeout: 40000 }).catch((e) => hits.push({ type: 'reload', text: e.message }));
  await p.waitForTimeout(6000);

  const snap = await p.evaluate(() => {
    const cur = [...document.querySelectorAll('a[aria-current]')].map(
      (a) => a.getAttribute('aria-current') + ' | ' + (a.textContent || '').trim().slice(0, 10)
    );
    return { path: location.pathname, ariaCurrent: cur, hasPortal: !!document.querySelector('nextjs-portal') };
  });
  console.log(JSON.stringify({ hydrationHits: hits.slice(0, 6), ...snap }, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});
