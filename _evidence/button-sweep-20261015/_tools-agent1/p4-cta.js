/* Phase 4: logged-in hero CTA click + secondary hero anchor; small final checks. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const steps = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 400)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  await page.goto('http://localhost:8800/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('#landing-nav', { timeout: 20000 }); await sleep(1800);
  await page.click('#btn-login-open'); await sleep(400);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 12000 }).catch(() => { }); await sleep(800);
  await page.click('#nav .cp-nav-item[data-nav="home"]'); await sleep(600);

  const ctaText = await page.$eval('#cta-demo', el => el.textContent.trim());
  await page.click('#cta-demo'); await sleep(2500);
  const st = await page.evaluate(() => ({ hash: location.hash, topbar: document.getElementById('topbar-title').textContent.trim(), frameVisible: !document.getElementById('frame-view').classList.contains('cp-hidden') }));
  let fr = null;
  for (let i = 0; i < 20; i++) { fr = page.frames().find(f => f.url().includes(':3001')); if (fr) break; await sleep(500); }
  const finfo = fr ? await fr.evaluate(() => ({ url: location.href, title: document.title })).catch(e => ({ err: String(e) })) : { err: 'no-frame' };
  rec({ area: 'hero-cta-loggedin', ctl: ctaText, action: 'click', after: { ...st, frame: finfo }, pass: st.hash.includes('ecommerce-ops') && st.frameVisible });
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-54-cta-loggedin-p02.png') });

  await page.click('#nav .cp-nav-item[data-nav="home"]'); await sleep(800);
  await page.evaluate(() => scrollTo(0, 0)); await sleep(300);
  const second = await page.$eval('.lp-hero a[href="#lp-modules"]', el => el.textContent.trim()).catch(() => null);
  if (second) {
    await page.click('.lp-hero a[href="#lp-modules"]'); await sleep(1200);
    const y = await page.evaluate(() => Math.round(scrollY));
    const vis = await page.evaluate(() => { const r = document.getElementById('lp-modules').getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; });
    rec({ area: 'hero-secondary', ctl: second, action: 'click', after: { scrollY: y, sectionVisible: vis }, pass: vis });
  } else {
    rec({ area: 'hero-secondary', ctl: '看十大模块与实测数据 ↓', action: 'not-found', pass: false });
  }
  fs.writeFileSync(path.join(OUT, 'p4-result.json'), JSON.stringify({ steps }, null, 2));
  console.log('P4 DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });