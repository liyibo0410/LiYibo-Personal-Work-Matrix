/* Phase 3b: complete local tests via http://localhost:8800 (IS_LOCAL=true path) + 127.0.0.1 defect repro + resume owner channel. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const OWNER_PW = fs.readFileSync('D:\\software\\PycharmProjects\\作品矩阵\\_runtime\\owner_password.txt', 'utf-8').trim();
const steps = [];
const logs = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 420)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shot = (page, name) => page.screenshot({ path: path.join(OUT, name) });
const PORTS = { p01: 5173, p02: 3001, p03: 5174, p04: 8041, p05: 8770, p06: 8060, p07: 8070, p08: 8080, p09: 8090, p10: 8101 };

function attach(page) {
  page.on('console', m => logs.push({ t: 'console', type: m.type(), text: m.text().slice(0, 260), url: (m.location() || {}).url }));
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 400) }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url().slice(0, 180), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url().slice(0, 180) }); });
}

async function frameByPort(page, id) {
  const port = ':' + PORTS[id];
  const frames = page.frames().filter(f => f.url().includes(port));
  return frames[frames.length - 1] || null;
}

async function login(page) {
  await page.click('#btn-login-open'); await sleep(400);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123');
  await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 15000 }).catch(() => { });
  await sleep(700);
}

async function mount(page, id, label, shotName) {
  await page.click(`#nav .cp-nav-item[data-nav="${id}"]`);
  await page.waitForFunction((id) => { const f = document.getElementById('module-frame'); return f && String(f.src).includes('/' + id + '/'); }, id, { timeout: 8000 }).catch(() => { });
  await sleep(400);
  const src = await page.$eval('#module-frame', f => f.src).catch(() => null);
  let fr = null;
  for (let i = 0; i < 40; i++) { fr = await frameByPort(page, id); if (fr && fr.url() !== 'about:blank') break; await sleep(500); }
  let finfo = null;
  if (!fr) finfo = { err: 'frame-not-found' };
  else {
    try {
      await fr.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => { });
      await sleep(2000);
      finfo = await fr.evaluate(() => ({
        url: location.href, title: document.title,
        textLen: (document.body ? document.body.innerText : '').length,
        snippet: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 130),
        rootKids: (document.querySelector('#app,#root,#__next') || document.body).children.length,
        theme: document.documentElement.getAttribute('data-theme')
      }));
    } catch (e) { finfo = { err: String(e).slice(0, 150) }; }
  }
  const banner = await page.evaluate(() => { const b = document.getElementById('svc-banner'); return b && getComputedStyle(b).display !== 'none' ? b.innerText.replace(/\s+/g, ' ').slice(0, 150) : null; });
  const pass = !!(finfo && !finfo.err && (finfo.textLen > 60 || finfo.rootKids > 1));
  rec({ area: 'localhost-mount', ctl: label + '(' + id + ')', action: 'click', src, banner, finfo, pass });
  if (shotName) await shot(page, shotName);
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });

  /* Part A: 127.0.0.1 defect repro (public URL in iframe from local shell) */
  const pa = await ctx.newPage(); attach(pa);
  await pa.goto('http://127.0.0.1:8800/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await pa.waitForSelector('#landing-nav', { timeout: 20000 }); await sleep(2000);
  await login(pa);
  await pa.click('#nav .cp-nav-item[data-nav="p01"]'); await sleep(3500);
  const a1 = await pa.$eval('#module-frame', f => f.src).catch(() => null);
  const bannerA = await pa.evaluate(() => { const b = document.getElementById('svc-banner'); return b ? b.innerText.replace(/\s+/g, ' ').slice(0, 160) : null; });
  rec({ area: 'defect-repro-127001', ctl: '127.0.0.1:8800 外壳挂载 p01', action: 'click', after: { src: a1, banner: bannerA }, pass: !!(a1 && a1.includes('39.96.200.45')), note: '预期挂本机 5173；实测指向公网隧道 URL（IS_LOCAL 正则含 $ 锚点，127.0.0.1 未命中）' });
  await shot(pa, 'agent1-shell-44-127001-iframe-points-to-public.png');
  await pa.close();

  /* Part B: localhost:8800 full local pass */
  const page = await ctx.newPage(); attach(page);
  await page.goto('http://localhost:8800/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('#landing-nav', { timeout: 20000 }); await sleep(2000);
  await login(page);
  const srcP01 = await (async () => { await page.click('#nav .cp-nav-item[data-nav="p01"]'); await sleep(1200); return page.$eval('#module-frame', f => f.src); })();
  rec({ area: 'localhost-mount', ctl: 'localhost:8800 外壳挂载 p01 的 src', action: 'click', after: { src: srcP01 }, pass: !!(srcP01 && srcP01.includes('localhost:5173')), note: 'localhost 命中 IS_LOCAL，挂本机端口' });

  const shots = { p01: 'agent1-shell-45-localhost-p01.png', p02: 'agent1-shell-46-localhost-p02.png', p04: 'agent1-shell-47-localhost-p04.png', p05: 'agent1-shell-48-localhost-p05.png', p06: 'agent1-shell-49-localhost-p06.png' };
  const list = [['p01', 'AI 客服'], ['p02', '运营助手'], ['p05', '合同审批'], ['p09', '销售考核'], ['p03', 'NL2SQL 问数'], ['p04', 'RAG 知识库'], ['p07', '素材中心'], ['p08', '直播切片'], ['p10', '模型微调平台'], ['p06', '数据中台']];
  for (const [id, label] of list) { await mount(page, id, label, shots[id] || null); }

  /* theme postMessage on 3 modules */
  const tc = [];
  for (const id of ['p09', 'p03', 'p10']) {
    await mount(page, id, '主题抽查前置挂载', null);
    const before = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    let fr = await frameByPort(page, id); const fb = fr ? await fr.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a') : 'no-frame';
    await page.click('#btn-theme'); await sleep(900);
    const after = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    fr = await frameByPort(page, id); const fa = fr ? await fr.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a') : 'no-frame';
    tc.push({ id, before, fb, after, fa, pass: after !== before && fa === after });
    if (id === 'p10') await shot(page, 'agent1-shell-50-localhost-theme-dark-p10.png');
  }
  rec({ area: 'theme-postmessage', ctl: '◐ 主题下发 p09/p03/p10 (localhost)', action: 'toggle x3', after: tc, pass: tc.every(x => x.pass) });
  if (tc.length && tc[tc.length - 1].after === 'dark') { await page.click('#btn-theme'); await sleep(600); }

  /* resume modal: owner channel (currently non-owner since fresh origin) → verify → save → reset */
  await page.click('#nav .cp-nav-item[data-nav="home"]'); await sleep(700);
  await page.evaluate(() => document.getElementById('lp-resume')?.scrollIntoView({ block: 'start' })); await sleep(700);
  await page.click('#btn-resume-settings'); await sleep(600);
  const r0 = await page.evaluate(() => ({ saveText: document.getElementById('rs-save').textContent.trim(), gateVisible: getComputedStyle(document.getElementById('rs-owner-gate')).display !== 'none' }));
  rec({ area: 'resume-modal', ctl: '打开(未登录作者通道)', action: 'click', after: r0, pass: r0.gateVisible && r0.saveText.includes('仅本机预览') });
  await page.fill('#rs-owner-pass', OWNER_PW); await page.click('#rs-owner-login'); await sleep(1300);
  const r1 = await page.evaluate(() => ({ okVisible: getComputedStyle(document.getElementById('rs-owner-ok')).display !== 'none', okText: document.getElementById('rs-owner-ok').textContent.trim(), saveText: document.getElementById('rs-save').textContent.trim(), err: document.getElementById('rs-error').textContent.trim() }));
  rec({ area: 'resume-modal', ctl: '作者通道登录 (本机 owner 口令)', action: 'submit', after: r1, pass: r1.okVisible && r1.saveText === '保存为全站默认' });
  await shot(page, 'agent1-shell-51-localhost-resume-owner-channel.png');
  await page.fill('#rs-name-in', 'A1 材料全站测试-恢复中');
  await page.click('#rs-save'); await sleep(1600);
  const r2 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name }));
  rec({ area: 'resume-modal', ctl: '保存为全站默认 (owner) — 稍后恢复原状', action: 'click', after: r2, pass: r2.apiName === 'A1 材料全站测试-恢复中' });
  await shot(page, 'agent1-shell-52-localhost-resume-owner-saved.png');
  await page.click('#btn-resume-settings'); await sleep(500);
  await page.click('#rs-reset'); await sleep(1600);
  const r3 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name }));
  rec({ area: 'resume-modal', ctl: '恢复默认 (owner→出厂值) — 稍后整体恢复原状', action: 'click', after: r3, pass: r3.apiName === '李奕波' });
  await shot(page, 'agent1-shell-53-localhost-resume-owner-reset.png');

  /* dots vs health on localhost */
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
  rec({ area: 'sidebar-health', ctl: '10 个探活点 vs /api/services/health (localhost)', action: 'read', after: dotState, pass: dotsMatch });

  fs.writeFileSync(path.join(OUT, 'p3b-result.json'), JSON.stringify({ ts: new Date().toISOString(), steps, logs }, null, 2));
  const errs = logs.filter(l => l.t === 'pageerror' || (l.t === 'console' && l.type === 'error') || l.t.startsWith('http4') || l.t.startsWith('http5') || l.t === 'reqfail');
  console.log('P3B DONE. steps=' + steps.length + ' errs=' + errs.length);
  console.log(JSON.stringify(errs.slice(0, 25), null, 1).slice(0, 3000));
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p3b-fatal.json'), JSON.stringify({ error: String(e), steps, logs }, null, 2)); process.exit(1); });