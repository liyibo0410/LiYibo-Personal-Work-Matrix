/* Phase 6: remaining small controls: brand anchor, backdrop closes, rs-pdf-view popup, mobile menu button. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.SHELL_BASE || 'http://39.96.200.45:8070';
const steps = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 400)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = (page, name) => page.screenshot({ path: path.join(OUT, name) });

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#landing-nav', { timeout: 25000 }); await sleep(2200);

  // 1) brand anchor #/ click
  await page.click('#landing-nav a[href="#/"]'); await sleep(900);
  const b1 = await page.evaluate(() => ({ hash: location.hash, topbar: document.getElementById('topbar-title').textContent.trim(), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden') }));
  rec({ area: 'nav-anchor', ctl: '品牌名锚点(#/)', action: 'click', after: b1, pass: b1.homeVisible });

  // 2) login modal backdrop close
  await page.click('#btn-login-open'); await sleep(600);
  await page.click('#login-modal', { position: { x: 12, y: 12 } });
  await sleep(500);
  const b2 = await page.evaluate(() => document.getElementById('login-modal').classList.contains('cp-hidden'));
  rec({ area: 'login-modal', ctl: '点击遮罩空白处关闭', action: 'click', after: { closed: b2 }, pass: b2 });

  // 3) rs-pdf-view click → popup/download
  await page.evaluate(() => document.getElementById('lp-resume')?.scrollIntoView({ block: 'start' })); await sleep(700);
  const popP = page.waitForEvent('popup', { timeout: 20000 }).catch(() => null);
  const dlP = page.waitForEvent('download', { timeout: 20000 }).catch(() => null);
  await page.click('#rs-pdf-view');
  const evt = await Promise.race([
    popP.then(p => p ? { kind: 'popup', url: p.url() } : null),
    dlP.then(d => d ? { kind: 'download', name: d.suggestedFilename() } : null),
    sleep(21000).then(() => ({ kind: 'none' }))
  ]);
  rec({ area: 'resume', ctl: '在线预览 (rs-pdf-view)', action: 'click', after: evt, pass: evt && evt.kind !== 'none' && !(evt.url && !/portfolio\.pdf/.test(evt.url)) });
  const pp = await popP; if (pp) await pp.close().catch(() => { });
  const dl = await dlP; if (dl) { dl.delete().catch(() => { }); }

  // 4) resume modal backdrop close
  await page.click('#btn-resume-settings'); await sleep(600);
  const open1 = await page.evaluate(() => document.getElementById('resume-settings').style.display !== 'none');
  await page.click('#resume-settings', { position: { x: 12, y: 12 } }); await sleep(500);
  const closed1 = await page.evaluate(() => document.getElementById('resume-settings').style.display === 'none');
  rec({ area: 'resume-modal', ctl: '点击遮罩空白处关闭', action: 'click', after: { wasOpen: open1, closedNow: closed1 }, pass: open1 && closed1 });

  // 5) mobile ☰ button
  await page.setViewportSize({ width: 390, height: 844 }); await sleep(700);
  const menuVisible = await page.evaluate(() => { const b = document.getElementById('btn-menu'); return getComputedStyle(b).display !== 'none'; });
  let toggled = null;
  if (menuVisible) {
    const before = await page.evaluate(() => document.getElementById('sidebar').className);
    await page.click('#btn-menu'); await sleep(700);
    const after = await page.evaluate(() => document.getElementById('sidebar').className);
    toggled = { before, after, changed: before !== after };
    await shot(page, 'agent1-shell-60-mobile-menu.png');
  }
  rec({ area: 'topbar', ctl: '☰ 菜单 (390px)', action: 'click', after: { menuVisible, toggled }, pass: menuVisible && toggled && toggled.changed });

  fs.writeFileSync(path.join(OUT, 'p6-result.json'), JSON.stringify({ base: BASE, steps }, null, 2));
  console.log('P6 DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p6-fatal.json'), JSON.stringify({ error: String(e), steps }, null, 2)); process.exit(1); });