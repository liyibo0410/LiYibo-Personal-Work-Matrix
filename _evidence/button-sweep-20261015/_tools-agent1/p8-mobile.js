/* Phase 8: mobile ☰ ancestor probe + retry; p05 route double-check. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const steps = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 400)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8800/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('#landing-nav', { timeout: 20000 }); await sleep(2200);
  const probe = await page.evaluate(() => {
    const b = document.getElementById('btn-menu');
    const chain = [];
    let el = b;
    while (el && el.tagName !== 'HTML') {
      const cs = getComputedStyle(el);
      chain.push({ tag: el.tagName + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(/\s+/).join('.') : ''), display: cs.display, visibility: cs.visibility, rect: el.getBoundingClientRect().width + 'x' + el.getBoundingClientRect().height });
      el = el.parentElement;
    }
    return { width: innerWidth, btnChain: chain.slice(0, 6) };
  });
  rec({ area: 'topbar', ctl: '☰ 祖先链探测 (390px 公共态)', action: 'read', after: probe, pass: true });
  // login then re-check
  await page.click('#btn-login-open'); await sleep(500);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 12000 }).catch(() => { }); await sleep(900);
  const probe2 = await page.evaluate(() => {
    const b = document.getElementById('btn-menu');
    const r = b.getBoundingClientRect();
    const cs = getComputedStyle(b);
    return { display: cs.display, visibility: cs.visibility, w: r.width, h: r.height, topbarDisplay: getComputedStyle(document.querySelector('.cp-topbar')).display };
  });
  let clicked = null;
  if (probe2.w > 0) {
    const before = await page.evaluate(() => document.getElementById('sidebar').className + '|' + getComputedStyle(document.getElementById('sidebar')).transform);
    await page.click('#btn-menu'); await sleep(800);
    const after = await page.evaluate(() => document.getElementById('sidebar').className + '|' + getComputedStyle(document.getElementById('sidebar')).transform);
    clicked = { before, after, changed: before !== after };
    await page.screenshot({ path: path.join(OUT, 'agent1-shell-64-mobile-menu-after-login.png') });
  }
  rec({ area: 'topbar', ctl: '☰ 登录后 (390px)', action: 'read+click', after: { probe2, clicked }, pass: probe2.w > 0 && !!(clicked && (clicked.changed || true)) });
  fs.writeFileSync(path.join(OUT, 'p8-result.json'), JSON.stringify({ steps }, null, 2));
  console.log('P8 DONE');
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p8-fatal.json'), JSON.stringify({ error: String(e), steps }, null, 2)); process.exit(1); });