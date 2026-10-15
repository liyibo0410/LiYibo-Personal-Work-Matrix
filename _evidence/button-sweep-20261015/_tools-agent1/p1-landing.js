/* Phase 1: landing page interactions (nav anchors, CTA, module-card gates, theme, PDF, login modal, login). */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.SHELL_BASE || 'http://39.96.200.45:8070';
const steps = [];
const logs = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 400)); };

function attach(page) {
  page.on('console', m => logs.push({ t: 'console', type: m.type(), text: m.text().slice(0, 400), url: (m.location() || {}).url }));
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 600) }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url(), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url() }); });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function visible(page, sel) { return page.evaluate(s => { const el = document.querySelector(s); if (!el) return false; const st = getComputedStyle(el); return st.display !== 'none' && st.visibility !== 'hidden' && el.getClientRects().length > 0; }, sel); }

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  attach(page);

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#landing-nav', { timeout: 25000 });
  await sleep(2500);

  /* T1: top-nav anchors */
  const anchors = await page.$$eval('#landing-nav a', as => as.map(a => ({ text: a.textContent.replace(/\s+/g, ' ').trim(), href: a.getAttribute('href') })));
  for (const a of anchors) {
    if (!a.href || !a.href.startsWith('#lp-')) continue;
    const sel = `#landing-nav a[href="${a.href}"]`;
    const before = await page.evaluate(() => ({ y: Math.round(scrollY), hash: location.hash }));
    await page.click(sel);
    await sleep(1300);
    const after = await page.evaluate((sec) => {
      const el = document.querySelector(sec);
      const r = el ? el.getBoundingClientRect() : null;
      return { y: Math.round(scrollY), hash: location.hash, secTop: r ? Math.round(r.top) : null, secVisible: !!r && r.top < innerHeight && r.bottom > 0 };
    }, a.href);
    rec({ area: 'nav-anchor', ctl: a.text, action: 'click', before, after, pass: after.secVisible });
    if (a.href === '#lp-modules') await page.screenshot({ path: path.join(OUT, 'agent1-shell-03-nav-modules.png') });
    if (a.href === '#lp-resume') await page.screenshot({ path: path.join(OUT, 'agent1-shell-04-nav-resume.png') });
  }

  /* content dumps for evidence/proof of rendered regions */
  const dumps = await page.evaluate(() => {
    const t = s => { const el = document.querySelector(s); return el ? el.innerText.replace(/\n{3,}/g, '\n\n').slice(0, 2600) : null; };
    return { evidenceSection: t('#lp-evidence'), archSection: t('#lp-arch'), boundarySection: t('#lp-boundary'), aboutSection: t('#lp-about'), resumeSection: t('#lp-resume') };
  });
  fs.writeFileSync(path.join(OUT, 'p1-content-dumps.json'), JSON.stringify(dumps, null, 2));

  /* T2: hero CTA */
  await page.evaluate(() => scrollTo(0, 0));
  await sleep(600);
  const ctaText = await page.$eval('#cta-demo', el => el.textContent.trim());
  const ctaHref = await page.$eval('#cta-demo', el => el.getAttribute('href'));
  await page.click('#cta-demo');
  await sleep(800);
  const ctaModal = { visible: await visible(page, '#login-modal'), reason: await page.$eval('#login-reason', el => el.textContent.trim()).catch(() => null), hash: await page.evaluate(() => location.hash) };
  rec({ area: 'hero-cta', ctl: '进入在线演示/登录，进入演示 · 旗舰 P02', ctlText: ctaText, href: ctaHref, action: 'click', after: ctaModal, pass: ctaModal.visible });
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-05-cta-login-modal.png') });
  await page.click('#btn-login-close');
  await sleep(500);
  rec({ area: 'login-modal', ctl: '先随便看看(btn-login-close)', action: 'click', after: { modalVisible: await visible(page, '#login-modal'), hash: await page.evaluate(() => location.hash), appPublic: await page.evaluate(() => document.body.classList.contains('cp-public')) }, pass: !(await visible(page, '#login-modal')) });

  /* T3: module cards gate (10) */
  const cards = await page.$$eval('#matrix .lp-mod', ms => ms.map(m => ({
    name: (m.querySelector('.cp-agent-name') || {}).textContent.trim(),
    href: (m.querySelector('a[href^="#/workspace/"]') || {}).getAttribute ? m.querySelector('a[href^="#/workspace/"]').getAttribute('href') : null
  })));
  let firstCard = true;
  for (const c of cards) {
    await page.evaluate(() => scrollTo(0, 0));
    await page.click(`#matrix a[href="${c.href}"]`);
    let ok = false;
    try { await page.waitForSelector('#login-modal:not(.cp-hidden)', { timeout: 4000 }); ok = true; } catch (e) { }
    const reason = await page.$eval('#login-reason', el => el.textContent.trim()).catch(() => null);
    rec({ area: 'module-card', ctl: c.name + ' 进入演示', href: c.href, action: 'click', after: { modalVisible: ok, reasonSnippet: reason ? reason.slice(0, 120) : null, hash: await page.evaluate(() => location.hash) }, pass: ok });
    if (ok && firstCard) { await page.screenshot({ path: path.join(OUT, 'agent1-shell-06-card-gate-modal.png') }); firstCard = false; }
    await page.click('#btn-login-close').catch(() => { });
    await sleep(350);
  }

  /* T4: theme toggle (landing) */
  const theme0 = await page.evaluate(() => ({ theme: document.documentElement.getAttribute('data-theme'), ls: Object.keys(localStorage) }));
  await page.click('#btn-theme-public');
  await sleep(500);
  const theme1 = await page.evaluate(() => ({ theme: document.documentElement.getAttribute('data-theme'), ls: JSON.stringify(Object.fromEntries(Object.entries(localStorage))) }));
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-07-theme-dark-landing.png') });
  await page.click('#btn-theme-public');
  await sleep(500);
  const theme2 = await page.evaluate(() => ({ theme: document.documentElement.getAttribute('data-theme') }));
  rec({ area: 'theme', ctl: '◐ (btn-theme-public)', action: 'click x2', before: theme0, afterDark: { theme: theme1.theme, ls: theme1.ls }, afterBack: theme2, pass: theme0.theme !== theme1.theme && theme2.theme === theme0.theme });

  /* T5: PDF links */
  const pdfFetch = await page.evaluate(async () => {
    const out = {};
    for (const id of ['rs-pdf-dl', 'rs-pdf-view']) {
      const href = document.getElementById(id).getAttribute('href');
      try { const r = await fetch(href); const b = await r.arrayBuffer(); out[id] = { href, status: r.status, type: r.headers.get('content-type'), bytes: b.byteLength }; }
      catch (e) { out[id] = { href, error: String(e) }; }
    }
    return out;
  });
  rec({ area: 'resume', ctl: 'PDF fetch check (dl+view)', action: 'fetch', after: pdfFetch, pass: pdfFetch['rs-pdf-dl'] && pdfFetch['rs-pdf-dl'].status === 200 });

  const dlP = page.waitForEvent('download', { timeout: 20000 }).catch(() => null);
  const popP = page.waitForEvent('popup', { timeout: 20000 }).catch(() => null);
  await page.click('#rs-pdf-dl');
  const evt = await Promise.race([dlP.then(d => d ? { kind: 'download', name: d.suggestedFilename() } : null), popP.then(p => p ? { kind: 'popup', url: p.url() } : null), sleep(21000).then(() => ({ kind: 'none' }))]);
  rec({ area: 'resume', ctl: '下载完整材料 PDF (rs-pdf-dl)', action: 'click', after: evt, pass: evt && evt.kind !== 'none' });
  const dl = await dlP; if (dl) { try { await dl.saveAs(path.join(OUT, 'agent1-shell-31-resume-downloaded.pdf')); } catch (e) { } dl.delete().catch(() => { }); }
  const pp = await popP; if (pp) { const u = pp.url(); await pp.close().catch(() => { }); rec({ area: 'resume', ctl: 'rs-pdf-view popup', action: 'auto-check', after: { url: u }, pass: /portfolio\.pdf/.test(u) }); }

  /* T6: login modal flow */
  await page.click('#btn-login-open');
  await sleep(600);
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-08-login-modal.png') });
  const reasonDefault = await page.$eval('#login-reason', el => el.textContent.trim());
  const chipResults = [];
  const chips = await page.$$('#demo-accounts .cp-demo-chip');
  for (const chip of chips) {
    const label = (await chip.textContent()).trim();
    await chip.click(); await sleep(150);
    const vals = await page.evaluate(() => ({ u: document.getElementById('login-user').value, p: document.getElementById('login-pass').value }));
    chipResults.push({ label, u: vals.u, p: vals.p });
  }
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-09-login-chips-filled.png') });
  rec({ area: 'login-modal', ctl: '演示账号 chips x5', action: 'click', after: chipResults, pass: chipResults.length === 5 && chipResults.every(c => c.p === c.u + '123') });

  await page.fill('#login-user', 'owner');
  await page.fill('#login-pass', 'wrong-pass-123');
  await page.click('#login-btn');
  await sleep(1800);
  const errState = await page.evaluate(() => ({ err: document.getElementById('login-err').textContent.trim(), modalVisible: !document.getElementById('login-modal').classList.contains('cp-hidden'), btn: document.getElementById('login-btn').textContent.trim() }));
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-10-login-error.png') });
  rec({ area: 'login-modal', ctl: '错误口令提交', action: 'submit owner/wrong-pass-123', after: errState, pass: !!errState.err && errState.modalVisible });

  await page.fill('#login-user', 'owner');
  await page.fill('#login-pass', 'owner123');
  await page.click('#login-btn');
  let entered = false;
  try { await page.waitForSelector('body:not(.cp-public)', { timeout: 12000 }); entered = true; } catch (e) { }
  await sleep(1200);
  const appState = await page.evaluate(() => ({
    bodyPublic: document.body.classList.contains('cp-public'),
    landingHidden: document.getElementById('landing-nav').classList.contains('cp-hidden'),
    appVisible: !document.getElementById('app-view').classList.contains('cp-hidden'),
    topbar: document.getElementById('topbar-title').textContent.trim(),
    badge: document.getElementById('user-badge').innerText.replace(/\s+/g, ' ').trim(),
    hash: location.hash,
    ss: Object.keys(sessionStorage)
  }));
  await page.screenshot({ path: path.join(OUT, 'agent1-shell-11-app-entered-owner.png'), fullPage: false });
  rec({ area: 'login-modal', ctl: '正确口令提交 owner/owner123', action: 'submit', after: appState, pass: entered && !appState.bodyPublic });
  rec({ area: 'login-modal', ctl: 'demo-accounts 小字/默认 reason', action: 'read', after: { reasonDefault }, pass: true });

  fs.writeFileSync(path.join(OUT, 'p1-result.json'), JSON.stringify({ base: BASE, steps, logs }, null, 2));
  console.log('P1 DONE. steps=' + steps.length + ' logs=' + logs.length);
  console.log('console/page errors:', JSON.stringify(logs.filter(l => l.t === 'pageerror' || (l.t === 'console' && l.type === 'error') || l.t.startsWith('http4') || l.t.startsWith('http5') || l.t === 'reqfail').slice(0, 20)));
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p1-fatal.json'), JSON.stringify({ error: String(e), steps, logs }, null, 2)); process.exit(1); });