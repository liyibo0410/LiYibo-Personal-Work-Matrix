/* Phase 7: public iframe final URLs for p02/p04/p05 (redirect-404 proof) + mobile menu at initial load. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = 'http://39.96.200.45:8070';
const steps = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 430)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const nets = [];
  page.on('response', r => { const u = r.url(); if (u.includes(':8090')) nets.push(r.status() + ' ' + u.slice(0, 150)); });
  page.on('requestfailed', r => { if (r.url().includes(':8090')) nets.push('FAIL ' + (r.failure() || {}).errorText + ' ' + r.url().slice(0, 150)); });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#landing-nav', { timeout: 25000 }); await sleep(2500);
  await page.click('#btn-login-open'); await sleep(500);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 15000 }).catch(() => { }); await sleep(600);

  for (const id of ['p02', 'p04', 'p05']) {
    nets.length = 0;
    await page.click(`#nav .cp-nav-item[data-nav="${id}"]`);
    await sleep(7000);
    const frames = page.frames().map(f => f.url()).filter(u => u && u !== 'about:blank');
    const iframeSrc = await page.$eval('#module-frame', f => f.src).catch(() => null);
    let frameBody = null;
    const fr = page.frames().find(f => /:8090\/(login|console\.html)/.test(f.url()) || f.url().includes('/' + id + '/'));
    if (fr) { frameBody = await fr.evaluate(() => ({ url: location.href, text: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 120) })).catch(e => ({ err: String(e).slice(0, 80) })); }
    rec({ area: 'public-redirect-proof', ctl: id, action: 'mount+7s', after: { iframeSrc, allFrames: frames, frameBody, nets: nets.slice(0, 8) }, pass: false, note: '看最终落点与状态码' });
    await page.screenshot({ path: path.join(OUT, 'agent1-shell-6' + (id === 'p02' ? '1' : id === 'p04' ? '2' : '3') + '-public-' + id + '-redirect404.png') });
  }
  await page.close();

  /* mobile menu at initial load */
  const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'zh-CN' });
  const mp = await mctx.newPage();
  await mp.goto('http://127.0.0.1:8800/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await mp.waitForSelector('#landing-nav', { timeout: 20000 }); await sleep(2000);
  const st = await mp.evaluate(() => ({
    width: innerWidth,
    menuDisplay: getComputedStyle(document.getElementById('btn-menu')).display,
    sidebarCls: document.getElementById('sidebar').className
  }));
  let toggled = null;
  if (st.menuDisplay !== 'none') {
    await mp.click('#btn-menu'); await sleep(800);
    const after = await mp.evaluate(() => document.getElementById('sidebar').className);
    toggled = { before: st.sidebarCls, after, changed: st.sidebarCls !== after };
    await mp.screenshot({ path: path.join(OUT, 'agent1-shell-64-mobile-menu-initial.png') });
  }
  rec({ area: 'topbar', ctl: '☰ 菜单 (初始 390px 加载)', action: 'read+click', after: { ...st, toggled }, pass: st.menuDisplay !== 'none' && (toggled ? toggled.changed : false) });
  await mctx.close();

  fs.writeFileSync(path.join(OUT, 'p7-result.json'), JSON.stringify({ steps }, null, 2));
  console.log('P7 DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p7-fatal.json'), JSON.stringify({ error: String(e), steps }, null, 2)); process.exit(1); });