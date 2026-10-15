/* Phase 0 recon: landing page structure dump + screenshots. Read-only against the shell. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.SHELL_BASE || 'http://39.96.200.45:8070';

function attach(page, logs) {
  page.on('console', m => logs.push({ t: 'console', type: m.type(), text: m.text().slice(0, 500) }));
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 800) }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url(), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url() }); });
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  const logs = []; attach(page, logs);

  let loaded = false;
  for (let i = 1; i <= 3; i++) {
    try {
      const resp = await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
      logs.push({ t: 'goto-ok', attempt: i, status: resp && resp.status() });
      loaded = true; break;
    } catch (e) { logs.push({ t: 'goto-err', attempt: i, text: String(e).slice(0, 300) }); await page.waitForTimeout(2000); }
  }
  await page.waitForSelector('#landing-nav', { timeout: 25000 }).catch(() => {});
  await page.waitForTimeout(3000);

  await page.screenshot({ path: path.join(OUT, 'agent1-shell-01-landing-public-full.png'), fullPage: true });
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-02-landing-public-viewport.png') });

  const info = await page.evaluate(() => {
    const vis = el => el.offsetParent !== null || el.getClientRects().length > 0;
    const q = s => Array.from(document.querySelectorAll(s));
    const clean = t => String(t || '').replace(/\s+/g, ' ').trim();
    const nav = q('#landing-nav a').map(a => ({ text: clean(a.textContent), href: a.getAttribute('href') }));
    const sections = q('#home-view section').map(s => ({ id: s.id, hasTitle: !!s.querySelector('h2,h3') }));
    const buttons = q('button').filter(vis).map(b => ({ id: b.id, text: clean(b.textContent).slice(0, 60), title: b.title }));
    const links = q('a').filter(vis).map(a => ({ id: a.id, text: clean(a.textContent).slice(0, 60), href: a.getAttribute('href') }));
    const mods = q('#matrix .lp-mod').map(m => ({
      name: clean((m.querySelector('.cp-agent-name') || {}).textContent),
      meta: clean((m.querySelector('.lp-mod-meta') || {}).textContent),
      svcTag: clean((m.querySelector('[data-svc-tag]') || {}).textContent),
      hasMock: !!m.querySelector('.lp-mod-mock'),
      demoHref: (m.querySelector('a[href^="#/workspace/"]') || {}).getAttribute ? m.querySelector('a[href^="#/workspace/"]').getAttribute('href') : null
    }));
    const statbar = q('#statbar .cp-stat').map(s => ({ v: clean((s.querySelector('.cp-stat-value') || {}).textContent), l: clean((s.querySelector('.cp-stat-label') || {}).textContent) }));
    return { title: document.title, hash: location.hash, nav, sections, buttons, links, mods, statbar, lsKeys: Object.keys(localStorage), ssKeys: Object.keys(sessionStorage) };
  });
  fs.writeFileSync(path.join(OUT, 'p0-recon.json'), JSON.stringify({ base: BASE, ts: new Date().toISOString(), loaded, info, logs }, null, 2));

  console.log('TITLE:', info.title);
  console.log('NAV:', JSON.stringify(info.nav));
  console.log('SECTIONS:', JSON.stringify(info.sections));
  console.log('BUTTONS:', JSON.stringify(info.buttons));
  console.log('KEY LINKS:', JSON.stringify(info.links.filter(l => l.id)));
  console.log('MODS n=' + info.mods.length, JSON.stringify(info.mods.map(m => m.name + '|' + m.svcTag + '|' + m.demoHref)));
  console.log('STATBAR:', JSON.stringify(info.statbar));
  console.log('LOGS tail:', JSON.stringify(logs.slice(-25)));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });