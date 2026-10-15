/* Probe: why did local shell mount public URLs? Read registry + iframe src + request hosts. */
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const c = await b.newContext({ viewport: { width: 1400, height: 900 } });
  const p = await c.newPage();
  const reqs = [];
  p.on('response', r => { const u = r.url(); if (u.includes('/shared/') || u.includes(':8800/') || u.includes('/api/')) reqs.push(r.status() + ' ' + u.slice(0, 130)); });
  await p.goto('http://127.0.0.1:8800/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await p.waitForTimeout(2500);
  const info = await p.evaluate(() => ({
    href: location.href, host: location.hostname,
    p01: window.CP_REGISTRY && window.CP_REGISTRY.services && window.CP_REGISTRY.services.p01,
    gateway: window.CP_REGISTRY && window.CP_REGISTRY.gateway
  }));
  console.log('HREF', info.href, '| HOST', info.host);
  console.log('P01 registry:', JSON.stringify(info.p01));
  console.log('gateway:', JSON.stringify(info.gateway));
  console.log('REQS(first 12):', JSON.stringify(reqs.slice(0, 12), null, 1));
  await p.click('#btn-login-open'); await p.waitForTimeout(400);
  await p.fill('#login-user', 'owner'); await p.fill('#login-pass', 'owner123'); await p.click('#login-btn');
  await p.waitForSelector('body:not(.cp-public)', { timeout: 12000 }).catch(() => {});
  await p.click('#nav .cp-nav-item[data-nav="p01"]');
  await p.waitForTimeout(1500);
  const src = await p.$eval('#module-frame', f => f.src);
  console.log('IFRAME SRC AFTER CLICK:', src);
  await b.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });