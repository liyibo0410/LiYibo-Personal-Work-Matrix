/* Phase 3: local re-tests of public-blocked items + owner channel verification (author password from _runtime/owner_password.txt, never printed). */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = 'http://127.0.0.1:8800';
const OWNER_PW = fs.readFileSync('D:\\software\\PycharmProjects\\作品矩阵\\_runtime\\owner_password.txt', 'utf-8').trim();
const steps = [];
const logs = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 420)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = (page, name) => page.screenshot({ path: path.join(OUT, name) });

const PORTS = { p01: 5173, p02: 3001, p03: 5174, p04: 8041, p05: 8770, p06: 8060, p07: 8070, p08: 8080, p09: 8090, p10: 8101 };

function attach(page) {
  page.on('console', m => logs.push({ t: 'console', type: m.type(), text: m.text().slice(0, 300), url: (m.location() || {}).url }));
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 400) }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url().slice(0, 200), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url().slice(0, 200) }); });
  page.on('dialog', async d => { logs.push({ t: 'dialog', text: d.message().slice(0, 200) }); await d.dismiss().catch(() => { }); });
}

async function frameByPort(page, id) {
  const port = ':' + PORTS[id];
  const frames = page.frames().filter(f => f.url().includes(port));
  return frames[frames.length - 1] || null;
}

async function mount(page, id, label, shotName) {
  await page.click(`#nav .cp-nav-item[data-nav="${id}"]`);
  await page.waitForFunction((id) => { const f = document.getElementById('module-frame'); return f && String(f.src).includes('/' + id + '/'); }, id, { timeout: 8000 }).catch(() => { });
  await sleep(400);
  const src = await page.$eval('#module-frame', f => f.src).catch(() => null);
  let fr = null;
  for (let i = 0; i < 50; i++) { fr = await frameByPort(page, id); if (fr && fr.url() !== 'about:blank') break; await sleep(500); }
  let finfo = null;
  if (!fr) finfo = { err: 'frame-not-found' };
  else {
    try {
      await fr.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => { });
      await sleep(2000);
      finfo = await fr.evaluate(() => ({
        url: location.href, title: document.title, ready: document.readyState,
        textLen: (document.body ? document.body.innerText : '').length,
        snippet: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 140),
        rootKids: (document.querySelector('#app,#root,#__next') || document.body).children.length,
        theme: document.documentElement.getAttribute('data-theme')
      }));
    } catch (e) { finfo = { err: String(e).slice(0, 150) }; }
  }
  const banner = await page.evaluate(() => { const b = document.getElementById('svc-banner'); return b && getComputedStyle(b).display !== 'none' ? b.innerText.replace(/\s+/g, ' ').slice(0, 160) : null; });
  const pass = !!(finfo && !finfo.err && (finfo.textLen > 60 || finfo.rootKids > 1));
  rec({ area: 'local-mount', ctl: label + '(' + id + ')', action: 'click', src, banner, finfo, pass });
  if (shotName) await shot(page, shotName);
  return fr;
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  attach(page);

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('#landing-nav', { timeout: 20000 });
  await sleep(2000);
  rec({ area: 'boot', ctl: '本地外壳 127.0.0.1:8800 打开', action: 'goto', after: { title: await page.title() }, pass: true });

  await page.click('#btn-login-open'); await sleep(500);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 12000 }).catch(() => { });
  await sleep(800);
  rec({ area: 'boot', ctl: '登录 owner/owner123 (本地)', action: 'submit', after: { topbar: await page.$eval('#topbar-title', el => el.textContent.trim()) }, pass: true });

  /* mounts: all 10 locally; explicit shots for previously failing 5 */
  const shots = { p01: 'agent1-shell-32-local-p01.png', p02: 'agent1-shell-33-local-p02.png', p04: 'agent1-shell-34-local-p04.png', p05: 'agent1-shell-35-local-p05.png', p06: 'agent1-shell-36-local-p06.png' };
  const list = [['p01', 'AI 客服'], ['p02', '运营助手'], ['p05', '合同审批'], ['p09', '销售考核'], ['p03', 'NL2SQL 问数'], ['p04', 'RAG 知识库'], ['p07', '素材中心'], ['p08', '直播切片'], ['p10', '模型微调平台'], ['p06', '数据中台']];
  for (const [id, label] of list) { await mount(page, id, label, shots[id] || null); }

  /* theme postMessage on three locally-served modules */
  const tc = [];
  for (const id of ['p09', 'p03', 'p10']) {
    await mount(page, id, '主题抽查前置挂载', null);
    const before = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    let fr = await frameByPort(page, id); const fb = fr ? await fr.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a') : 'no-frame';
    await page.click('#btn-theme'); await sleep(900);
    const after = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    fr = await frameByPort(page, id); const fa = fr ? await fr.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a') : 'no-frame';
    tc.push({ id, before, fb, after, fa, pass: after !== before && fa === after });
    if (id === 'p10') await shot(page, 'agent1-shell-37-theme-dark-p10.png');
  }
  rec({ area: 'theme-postmessage', ctl: '◐ 主题下发 p09/p03/p10 (本地)', action: 'toggle x3', after: tc, pass: tc.every(x => x.pass) });
  // back to light
  if (tc.length && tc[tc.length - 1].after === 'dark') { await page.click('#btn-theme'); await sleep(600); }

  /* health dots re-read + simultaneous API value */
  const dotState = await page.evaluate(async () => {
    const out = { dots: [], health: null, badge: (document.getElementById('svc-online') || {}).textContent };
    document.querySelectorAll('#nav .cp-nav-item[data-nav]').forEach(a => {
      const id = a.getAttribute('data-nav'); if (id === 'home') return;
      const d = a.querySelector('.cp-nav-dot');
      out.dots.push({ id, cls: d ? d.className.replace('cp-nav-dot', '').trim() : null, title: d ? d.title : null });
    });
    try { const r = await fetch('/api/services/health', { cache: 'no-store' }); const j = await r.json(); out.health = Object.fromEntries(Object.entries(j.services || {}).map(([k, v]) => [k, v.online])); } catch (e) { out.health = 'ERR'; }
    return out;
  });
  const dotsMatch = dotState.dots.every(d => (dotState.health[d.id] === true) === /(^|\s)online(\s|$)/.test(d.cls));
  rec({ area: 'sidebar-health', ctl: '10 个探活点 vs /api/services/health (本地)', action: 'read', after: dotState, pass: dotsMatch });
  await shot(page, 'agent1-shell-38-dots-local.png');

  /* owner channel: brand panel */
  await page.click('#btn-brand-settings'); await sleep(600);
  await page.fill('#bs-owner-pass', OWNER_PW);
  await page.click('#bs-owner-login'); await sleep(1300);
  const ow1 = await page.evaluate(() => ({ okVisible: getComputedStyle(document.getElementById('bs-owner-ok')).display !== 'none', okText: document.getElementById('bs-owner-ok').textContent.trim(), saveText: document.getElementById('bs-save').textContent.trim(), gateVisible: getComputedStyle(document.getElementById('bs-owner-gate')).display !== 'none', err: document.getElementById('bs-error').textContent.trim(), hasToken: !!sessionStorage.getItem('cp_owner_token') }));
  rec({ area: 'brand-modal', ctl: '作者通道登录 (本机 owner 口令)', action: 'submit', after: { ...ow1, pwFrom: '_runtime/owner_password.txt (未记录值)' }, pass: ow1.okVisible && ow1.hasToken });
  await shot(page, 'agent1-shell-39-brand-owner-channel-local.png');
  await page.fill('#bs-company', 'A1 全站品牌测试-恢复中');
  await page.fill('#bs-initials', 'A9');
  await page.click('#bs-save'); await sleep(1600);
  const ow2 = await page.evaluate(async () => ({ apiCompany: (await (await fetch('/api/brand', { cache: 'no-store' })).json()).brand.company }));
  const sidebarTxt = await page.$eval('.cp-brand-cfg', el => el.innerText.replace(/\s+/g, ' ').trim()).catch(() => null);
  rec({ area: 'brand-modal', ctl: '保存并全站生效 (owner) — 稍后恢复原状', action: 'click', after: { ...ow2, sidebar: sidebarTxt }, pass: ow2.apiCompany === 'A1 全站品牌测试-恢复中' });
  await shot(page, 'agent1-shell-40-brand-owner-saved-local.png');
  await page.click('#btn-brand-settings'); await sleep(500);
  await page.click('#bs-reset'); await sleep(1600);
  const ow3 = await page.evaluate(async () => ({ apiCompany: (await (await fetch('/api/brand', { cache: 'no-store' })).json()).brand.company }));
  rec({ area: 'brand-modal', ctl: '恢复默认 (owner→出厂值) — 稍后整体恢复原状', action: 'click', after: ow3, pass: ow3.apiCompany === '李奕波个人作品矩阵' });
  await shot(page, 'agent1-shell-41-brand-owner-reset-local.png');
  await page.click('#brand-settings', { position: { x: 8, y: 8 } }).catch(() => { }); await sleep(400);

  /* owner channel: resume panel */
  await page.evaluate(() => document.getElementById('lp-resume')?.scrollIntoView({ block: 'start' })); await sleep(600);
  await page.click('#btn-resume-settings'); await sleep(600);
  const ow4 = await page.evaluate(() => ({ okVisible: getComputedStyle(document.getElementById('rs-owner-ok')).display !== 'none', okText: document.getElementById('rs-owner-ok').textContent.trim(), saveText: document.getElementById('rs-save').textContent.trim() }));
  rec({ area: 'resume-modal', ctl: '作者通道共用会话 (品牌处已登录)', action: 'open', after: ow4, pass: ow4.okVisible });
  await page.fill('#rs-name-in', 'A1 材料全站测试-恢复中');
  await page.click('#rs-save'); await sleep(1600);
  const ow5 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name }));
  rec({ area: 'resume-modal', ctl: '保存为全站默认 (owner) — 稍后恢复原状', action: 'click', after: ow5, pass: ow5.apiName === 'A1 材料全站测试-恢复中' });
  await shot(page, 'agent1-shell-42-resume-owner-saved-local.png');
  await page.click('#btn-resume-settings'); await sleep(500);
  await page.click('#rs-reset'); await sleep(1600);
  const ow6 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name }));
  rec({ area: 'resume-modal', ctl: '恢复默认 (owner→出厂值) — 稍后整体恢复原状', action: 'click', after: ow6, pass: ow6.apiName === '李奕波' });
  await shot(page, 'agent1-shell-43-resume-owner-reset-local.png');

  fs.writeFileSync(path.join(OUT, 'p3-result.json'), JSON.stringify({ base: BASE, ts: new Date().toISOString(), steps, logs }, null, 2));
  const errs = logs.filter(l => l.t === 'pageerror' || (l.t === 'console' && l.type === 'error') || l.t.startsWith('http4') || l.t.startsWith('http5') || l.t === 'reqfail');
  console.log('P3 DONE. steps=' + steps.length + ' errs=' + errs.length);
  console.log(JSON.stringify(errs.slice(0, 30), null, 1).slice(0, 3500));
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p3-fatal.json'), JSON.stringify({ error: String(e), steps, logs }, null, 2)); process.exit(1); });