const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  const reqs = [];
  page.on('response', r => { if (r.url().includes('39.96.200.45')) reqs.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
  page.on('console', m => { if (m.type() === 'error') reqs.push(`CONSOLE-ERR ${m.text().slice(0, 200)}`); });

  await page.goto('http://39.96.200.45:8090/p06/', { waitUntil: 'load', timeout: 45000 }).catch(e => reqs.push('goto-fail ' + e.message));
  await page.waitForTimeout(5000);
  const p06 = await page.evaluate(() => ({
    badge: (document.getElementById('dash-badge') || {}).textContent,
    statCards: document.querySelectorAll('#dash-stats .stat-card').length,
    toasts: (document.getElementById('toast-container') || {}).innerText || '',
    navCount: document.querySelectorAll('.nav-item').length,
  }));
  console.log('P06-PUBLIC', JSON.stringify(p06));

  await page.goto('http://39.96.200.45:8090/p07/', { waitUntil: 'load', timeout: 45000 }).catch(e => reqs.push('goto-fail2 ' + e.message));
  await page.waitForTimeout(6000);
  const p07 = await page.evaluate(() => ({
    badges: (document.getElementById('status-badges') || {}).innerText || '',
    navCount: document.querySelectorAll('#nav .tab').length,
    contentHead: (document.getElementById('content') || {}).innerText?.slice(0, 200) || '',
    toast: (document.getElementById('toast') || {}).innerText || '',
  }));
  console.log('P07-PUBLIC', JSON.stringify(p07));
  console.log('REQS:'); reqs.slice(0, 60).forEach(r => console.log(' ', r));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });