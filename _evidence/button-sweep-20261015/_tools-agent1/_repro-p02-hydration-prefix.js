/* 监督窗口复现 v2：2.8 P02 水合告警 —— 经本地剥前缀代理（复刻公网 nginx /p02 分流）
 * 场景：登录后整页加载 http://127.0.0.1:18901/p02/?cp-theme=light
 * 预期（修复前）：浏览器 pathname=/p02/ 与服务端 pathname=/ 分叉 → aria-current/className 水合告警 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await browser.newPage();
  const hits = [];
  p.on('console', (m) => {
    const t = m.text();
    if (/did not match|didn't match|hydrat/i.test(t)) hits.push({ type: m.type(), text: t.slice(0, 500) });
  });
  p.on('pageerror', (e) => hits.push({ type: 'pageerror', text: String(e.message).slice(0, 300) }));

  // 先直连 3001 登录拿 cookie（cookie 按 host 存，端口无关）
  await p.goto('http://127.0.0.1:3001/login', { waitUntil: 'load', timeout: 40000 }).catch((e) => hits.push({ type: 'goto', text: e.message }));
  await p.waitForTimeout(2000);
  await p.fill('input[type="email"]', 'boss@example.com').catch(() => {});
  await p.fill('input[type="password"]', 'Test123456').catch(() => {});
  await p.click('button[type="submit"]').catch(() => {});
  await p.waitForTimeout(4000);

  // 关键一步：经代理以 /p02/ 前缀整页加载（等价公网挂载）
  await p.goto('http://127.0.0.1:18901/p02/?cp-theme=light', { waitUntil: 'load', timeout: 60000 }).catch((e) => hits.push({ type: 'goto-proxy', text: e.message }));
  await p.waitForTimeout(7000);

  const snap = await p.evaluate(() => {
    const cur = [...document.querySelectorAll('a[aria-current]')].map(
      (a) => a.getAttribute('aria-current') + ' | ' + (a.textContent || '').trim().slice(0, 10)
    );
    return { path: location.pathname + location.search, ariaCurrent: cur };
  });
  const out = { hits: hits.slice(0, 4), hitCount: hits.length, ...snap };
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});
