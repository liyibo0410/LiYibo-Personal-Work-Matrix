/* 监督窗口验证：P03 健康徽标（2.10）—— vite HMR 后徽标存在、取到真实状态、页面零报错 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await browser.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e.message).slice(0, 220)));
  p.on('console', (m) => {
    if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 220));
  });
  await p
    .goto('http://127.0.0.1:5174/', { waitUntil: 'load', timeout: 30000 })
    .catch((e) => errs.push('goto ' + e.message));
  await p.waitForTimeout(4500);
  const out = await p.evaluate(() => {
    const el = document.querySelector('.health-badge');
    const overlay = !!document.querySelector('vite-error-overlay');
    return {
      overlay,
      badge: el
        ? { text: el.textContent.trim(), cls: el.className, title: el.getAttribute('title') }
        : null,
    };
  });
  console.log(JSON.stringify({ ...out, errors: errs.slice(0, 8) }, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});
