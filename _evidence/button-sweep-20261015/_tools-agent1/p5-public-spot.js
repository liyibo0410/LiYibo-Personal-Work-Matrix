/* Phase 5: public spot-check of previously problematic module mounts (tunnel recovered). */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = 'http://39.96.200.45:8070';
const steps = [];
const logs = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 420)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PORTS = { p01: 8090, p02: 8090, p03: 8090, p04: 8090, p05: 8090, p06: 8090, p07: 8090, p08: 8090, p09: 8090, p10: 8090 };

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 300) }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url().slice(0, 180), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url().slice(0, 180) }); });

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#landing-nav', { timeout: 25000 }); await sleep(2500);
  await page.click('#btn-login-open'); await sleep(500);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 15000 }).catch(() => { }); await sleep(800);

  for (const id of ['p01', 'p02', 'p04', 'p05', 'p06']) {
    await page.click(`#nav .cp-nav-item[data-nav="${id}"]`);
    await page.waitForFunction((id) => { const f = document.getElementById('module-frame'); return f && String(f.src).includes('/' + id + '/'); }, id, { timeout: 8000 }).catch(() => { });
    await sleep(600);
    const src = await page.$eval('#module-frame', f => f.src).catch(() => null);
    let fr = null;
    for (let i = 0; i < 50; i++) { fr = page.frames().find(f => f.url().includes('/' + id + '/')); if (fr && fr.url() !== 'about:blank') break; await sleep(600); }
    let finfo = null;
    if (!fr) finfo = { err: 'frame-not-found' };
    else {
      try {
        await fr.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => { });
        await sleep(2500);
        finfo = await fr.evaluate(() => ({
          url: location.href, title: document.title,
          textLen: (document.body ? document.body.innerText : '').length,
          snippet: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 130),
          rootKids: (document.querySelector('#app,#root,#__next') || document.body).children.length
        }));
      } catch (e) { finfo = { err: String(e).slice(0, 150) }; }
    }
    const banner = await page.evaluate(() => { const b = document.getElementById('svc-banner'); return b && getComputedStyle(b).display !== 'none' ? b.innerText.replace(/\s+/g, ' ').slice(0, 150) : null; });
    const pass = !!(finfo && !finfo.err && (finfo.textLen > 60 || finfo.rootKids > 1));
    rec({ area: 'public-spot', ctl: id, action: 'click', src, banner, finfo, pass });
    await page.screenshot({ path: path.join(OUT, 'agent1-shell-5' + (5 + ['p01','p02','p04','p05','p06'].indexOf(id)) + '-public-' + id + '.png') });
  }
  fs.writeFileSync(path.join(OUT, 'p5-result.json'), JSON.stringify({ steps, logs }, null, 2));
  console.log('P5 DONE steps=' + steps.length);
  console.log(JSON.stringify(logs.slice(0, 15), null, 1).slice(0, 1800));
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p5-fatal.json'), JSON.stringify({ error: String(e), steps, logs }, null, 2)); process.exit(1); });