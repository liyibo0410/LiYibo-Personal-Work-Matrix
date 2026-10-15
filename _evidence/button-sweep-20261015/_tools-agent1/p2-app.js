/* Phase 2: app sidebar, module mounts, health dots, theme postMessage, unknown routes, logout, brand & resume modals. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.SHELL_BASE || 'http://39.96.200.45:8070';
const LOGO_PNG = 'D:\\software\\PycharmProjects\\作品矩阵\\projects\\p05-contract-review\\ui\\assets\\favicon.png';
const steps = [];
const logs = [];
const rec = (o) => { o.ts = new Date().toISOString(); steps.push(o); console.log('[rec]', JSON.stringify(o).slice(0, 460)); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function attach(page) {
  page.on('console', m => logs.push({ t: 'console', type: m.type(), text: m.text().slice(0, 400), url: (m.location() || {}).url }));
  page.on('pageerror', e => logs.push({ t: 'pageerror', text: String(e).slice(0, 600), url: (e.location && e.location() || {}).url }));
  page.on('requestfailed', r => logs.push({ t: 'reqfail', url: r.url(), err: (r.failure() || {}).errorText || '' }));
  page.on('response', r => { if (r.status() >= 400) logs.push({ t: 'http' + r.status(), url: r.url() }); });
  page.on('dialog', async d => { logs.push({ t: 'dialog', type: d.type(), text: d.message().slice(0, 300) }); await d.dismiss().catch(() => { }); });
}
const shot = (page, name) => page.screenshot({ path: path.join(OUT, name) });

async function frameFor(page, id) {
  const frames = page.frames().filter(f => f.url().includes('/' + id + '/') && /:\d+\//.test(f.url()));
  return frames[frames.length - 1] || null;
}

async function mountAndCheck(page, id, label, shotName) {
  await page.click(`#nav .cp-nav-item[data-nav="${id}"]`);
  await page.waitForFunction((id) => { const f = document.getElementById('module-frame'); return f && String(f.src).includes('/' + id + '/'); }, id, { timeout: 10000 }).catch(() => { });
  await sleep(500);
  const src = await page.$eval('#module-frame', f => f.src).catch(() => null);
  let fr = null;
  for (let i = 0; i < 44; i++) { fr = await frameFor(page, id); if (fr) break; await sleep(500); }
  let finfo = null;
  if (!fr) finfo = { err: 'frame-not-found' };
  else {
    try {
      await fr.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => { });
      await sleep(2200);
      finfo = await fr.evaluate(() => ({
        title: document.title, ready: document.readyState,
        textLen: (document.body ? document.body.innerText : '').length,
        snippet: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 150),
        rootKids: (document.querySelector('#app,#root') || document.body).children.length,
        theme: document.documentElement.getAttribute('data-theme')
      }));
    } catch (e) { finfo = { err: String(e).slice(0, 180) }; }
  }
  const banner = await page.evaluate(() => { const b = document.getElementById('svc-banner'); return b && getComputedStyle(b).display !== 'none' ? b.innerText.replace(/\s+/g, ' ').slice(0, 200) : null; });
  const pass = !!(fr && finfo && !finfo.err && (finfo.textLen > 60 || finfo.rootKids > 1));
  rec({ area: 'sidebar-mount', ctl: label + '(' + id + ')', action: 'click', src, banner, finfo, pass });
  if (shotName) await shot(page, shotName);
  return finfo;
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await ctx.newPage();
  attach(page);

  /* S1: unknown route, logged out */
  await page.goto(BASE + '/#/workspace/unknown-xyz', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#landing-nav', { timeout: 25000 });
  await sleep(2500);
  const unk1 = await page.evaluate(() => ({ hash: location.hash, topbar: document.getElementById('topbar-title').textContent.trim(), modalVisible: !document.getElementById('login-modal').classList.contains('cp-hidden'), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden'), frameVisible: !document.getElementById('frame-view').classList.contains('cp-hidden') }));
  rec({ area: 'route', ctl: '未知路由 #/workspace/unknown-xyz (未登录直接打开)', action: 'goto', after: unk1, pass: unk1.homeVisible && !unk1.frameVisible, note: '静默回落到作品集首页' });
  await shot(page, 'agent1-shell-12-unknownroute-public.png');

  /* S2: deep link to P02, logged out → login gate → login → mounts P02 */
  await page.goto(BASE + '/#/workspace/ecommerce-ops', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await sleep(2500);
  const dl = await page.evaluate(() => ({ hash: location.hash, modalVisible: !document.getElementById('login-modal').classList.contains('cp-hidden'), reason: document.getElementById('login-reason').textContent.trim().slice(0, 140) }));
  rec({ area: 'route', ctl: '深链 #/workspace/ecommerce-ops (未登录)', action: 'goto', after: dl, pass: dl.modalVisible });
  await shot(page, 'agent1-shell-13-deeplink-login-gate.png');
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123');
  await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 15000 }).catch(() => { });
  const p02a = await mountAndCheck(page, 'p02', '深链登录后自动挂载 P02 运营助手', 'agent1-shell-14-p02-mounted.png');

  /* S3: sidebar home + 10 modules */
  await page.click('#nav .cp-nav-item[data-nav="home"]'); await sleep(900);
  const homeBack = await page.evaluate(() => ({ topbar: document.getElementById('topbar-title').textContent.trim(), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden'), frameVisible: !document.getElementById('frame-view').classList.contains('cp-hidden') }));
  rec({ area: 'sidebar', ctl: '作品集首页(data-nav=home)', action: 'click', after: homeBack, pass: homeBack.homeVisible && !homeBack.frameVisible });
  const mods = [
    ['p01', 'AI 客服', 'agent1-shell-16-p01-mounted.png'], ['p02', '运营助手', null], ['p05', '合同审批', null], ['p09', '销售考核', null],
    ['p03', 'NL2SQL 问数', null], ['p04', 'RAG 知识库', null], ['p07', '素材中心', null], ['p08', '直播切片', 'agent1-shell-17-p08-mounted.png'],
    ['p10', '模型微调平台', null], ['p06', '数据中台', 'agent1-shell-15-p06-mounted.png']
  ];
  for (const [id, label, sh] of mods) { await mountAndCheck(page, id, label, sh); }

  /* S4: health dots + health api cross-check */
  await sleep(1500);
  const dots = await page.evaluate(async () => {
    const out = { dots: [], health: null };
    document.querySelectorAll('#nav .cp-nav-item[data-nav]').forEach(a => {
      const id = a.getAttribute('data-nav'); if (id === 'home') return;
      const d = a.querySelector('.cp-nav-dot');
      out.dots.push({ id, cls: d ? d.className : null, title: d ? d.title : null, label: a.querySelector('.cp-nav-label') ? a.querySelector('.cp-nav-label').textContent.trim() : '' });
    });
    try { const r = await fetch('/api/services/health', { cache: 'no-store' }); const j = await r.json(); out.health = Object.fromEntries(Object.entries(j.services || {}).map(([k, v]) => [k, v.online])); out.healthTs = j.checked_at; } catch (e) { out.health = 'ERR ' + e; }
    return out;
  });
  const dotGreen = dots.dots.filter(d => /(^|\s)online(\s|$)/.test(d.cls || '')).length;
  const healthOn = typeof dots.health === 'object' ? Object.values(dots.health).filter(Boolean).length : -1;
  rec({ area: 'sidebar-health', ctl: '10 个侧栏探活点 + svc-online badge', action: 'read', after: { dots: dots.dots, healthOnline: healthOn, badge: await page.$eval('#svc-online', el => el.textContent).catch(() => null) }, pass: dotGreen === 10 && healthOn === 10 });

  /* S5: theme toggle with modules mounted (postMessage check) */
  const themeChecks = [];
  async function themeStep(id) {
    await sleep(400);
    const before = { shell: await page.evaluate(() => document.documentElement.getAttribute('data-theme')), frame: null };
    const fr = await frameFor(page, id); if (fr) before.frame = await fr.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a');
    await page.click('#btn-theme'); await sleep(900);
    const after = { shell: await page.evaluate(() => document.documentElement.getAttribute('data-theme')), frame: null };
    const fr2 = await frameFor(page, id); if (fr2) after.frame = await fr2.evaluate(() => document.documentElement.getAttribute('data-theme')).catch(() => 'n/a');
    themeChecks.push({ id, before, after, pass: after.shell !== before.shell && after.frame === after.shell });
  }
  await themeStep('p06');
  await shot(page, 'agent1-shell-18-theme-dark-p06.png');
  await mountAndCheck(page, 'p02', '运营助手(主题抽查)', null); await themeStep('p02');
  await mountAndCheck(page, 'p07', '素材中心(主题抽查)', null); await themeStep('p07'); await themeStep('p07'); // back to light
  rec({ area: 'theme-postmessage', ctl: '◐ 切换后模块 iframe 跟随', action: 'toggle x4', after: themeChecks, pass: themeChecks.every(t => t.pass) });

  /* S6: unknown routes while logged in */
  await page.evaluate(() => { location.hash = '#/workspace/unknown-inapp'; }); await sleep(900);
  const unk2 = await page.evaluate(() => ({ hash: location.hash, topbar: document.getElementById('topbar-title').textContent.trim(), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden'), frameVisible: !document.getElementById('frame-view').classList.contains('cp-hidden') }));
  rec({ area: 'route', ctl: '未知路由 #/workspace/unknown-inapp (已登录)', action: 'set hash', after: unk2, pass: unk2.homeVisible && !unk2.frameVisible });
  await shot(page, 'agent1-shell-19-unknownroute-inapp.png');
  await page.evaluate(() => { location.hash = '#/garbage'; }); await sleep(700);
  const unk3 = await page.evaluate(() => ({ topbar: document.getElementById('topbar-title').textContent.trim(), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden') }));
  rec({ area: 'route', ctl: '乱码路由 #/garbage', action: 'set hash', after: unk3, pass: unk3.homeVisible });

  /* S7: logout */
  await page.click('#btn-logout'); await sleep(1200);
  const lo = await page.evaluate(() => ({ bodyPublic: document.body.classList.contains('cp-public'), landingVisible: !document.getElementById('landing-nav').classList.contains('cp-hidden'), frameVisible: !document.getElementById('frame-view').classList.contains('cp-hidden'), homeVisible: !document.getElementById('home-view').classList.contains('cp-hidden'), badge: document.getElementById('user-badge').innerText.trim(), ss: Object.keys(sessionStorage), hash: location.hash }));
  rec({ area: 'topbar', ctl: '⎋ 退出登录', action: 'click', after: lo, pass: lo.bodyPublic && lo.landingVisible && lo.ss.length === 0 });
  await shot(page, 'agent1-shell-20-after-logout.png');

  /* S8: re-login for brand/resume modals */
  await page.click('#btn-login-open'); await sleep(600);
  await page.fill('#login-user', 'owner'); await page.fill('#login-pass', 'owner123'); await page.click('#login-btn');
  await page.waitForSelector('body:not(.cp-public)', { timeout: 15000 }).catch(() => { }); await sleep(800);

  /* S9: brand modal */
  const navBrandText = () => page.$eval('#sidebar .cp-brand-name, #sidebar [data-cp-brand], .cp-brand-cfg', el => el.innerText.replace(/\s+/g, ' ').trim()).catch(() => null);
  await page.click('#btn-brand-settings'); await sleep(700);
  const bm0 = await page.evaluate(() => {
    const v = id => document.getElementById(id).value;
    return {
      company: v('bs-company'), name_en: v('bs-name-en'), subtitle: v('bs-subtitle'), tagline: v('bs-tagline'), version: v('bs-version'), initials: v('bs-initials'),
      saveText: document.getElementById('bs-save').textContent.trim(), gateVisible: getComputedStyle(document.getElementById('bs-owner-gate')).display !== 'none',
      previewImg: !!document.querySelector('#bs-logo-preview img')
    };
  });
  rec({ area: 'brand-modal', ctl: '⚙ 打开品牌设置', action: 'click', after: bm0, pass: true });
  await shot(page, 'agent1-shell-21-brand-modal.png');
  await page.fill('#bs-company', 'Agent1 测试品牌');
  await page.fill('#bs-name-en', 'Agent1 Test Mark');
  await page.fill('#bs-subtitle', '测试副题');
  await page.fill('#bs-tagline', '测试标语');
  await page.fill('#bs-version', 'v9.9.9');
  await page.fill('#bs-initials', 'A1');
  await page.setInputFiles('#bs-logo-file', LOGO_PNG);
  await sleep(1500);
  const bm1 = await page.evaluate(() => ({ previewImg: !!document.querySelector('#bs-logo-preview img'), logoDataLen: (document.getElementById('bs-logo-preview')._logoData || '').length }));
  rec({ area: 'brand-modal', ctl: '全部字段输入 + Logo 上传(p05 favicon.png)', action: 'fill+upload', after: bm1, pass: bm1.previewImg && bm1.logoDataLen > 100 });
  await shot(page, 'agent1-shell-22-brand-filled-logo.png');
  await page.click('#bs-clear-logo'); await sleep(400);
  const bm2 = await page.evaluate(() => ({ previewText: document.getElementById('bs-logo-preview').textContent.trim(), previewImg: !!document.querySelector('#bs-logo-preview img') }));
  rec({ area: 'brand-modal', ctl: '清除已上传图片', action: 'click', after: bm2, pass: !bm2.previewImg });
  await page.click('#bs-save'); await sleep(900);
  const bm3 = await page.evaluate(async () => {
    const api = await (await fetch('/api/brand', { cache: 'no-store' })).json();
    return { modalOpen: document.getElementById('brand-settings').style.display !== 'none', override: localStorage.getItem('cp_brand_override'), apiCompany: api.brand.company, navBrand: (document.querySelector('#sidebar-footer').previousElementSibling ? '' : (document.body.innerText.match(/Agent1 测试品牌/) || [null])[0]) };
  });
  const navTxtAfterLocal = await page.evaluate(() => (document.querySelector('.cp-brand') || {}).innerText || document.body.innerText.slice(0, 0));
  rec({ area: 'brand-modal', ctl: '保存（仅本机预览）', action: 'click', after: { ...bm3, sidebarBrand: await navBrandText(), pageHasMarker: await page.evaluate(() => document.body.innerText.includes('Agent1 测试品牌')) }, pass: !!bm3.override && bm3.apiCompany !== 'Agent1 测试品牌' });
  await shot(page, 'agent1-shell-23-brand-local-saved.png');
  await page.click('#btn-brand-settings'); await sleep(500);
  await page.click('#bs-reset'); await sleep(1000);
  const bm4 = await page.evaluate(async () => ({ override: localStorage.getItem('cp_brand_override'), apiCompany: (await (await fetch('/api/brand', { cache: 'no-store' })).json()).brand.company, pageHasMarker: document.body.innerText.includes('Agent1 测试品牌') }));
  rec({ area: 'brand-modal', ctl: '恢复默认(非 owner)', action: 'click', after: bm4, pass: !bm4.override && !bm4.pageHasMarker });
  await shot(page, 'agent1-shell-24-brand-reset.png');
  await page.click('#btn-brand-settings'); await sleep(500);
  await page.fill('#bs-owner-pass', 'owner123'); await page.click('#bs-owner-login'); await sleep(1200);
  const bm5 = await page.evaluate(() => ({ okVisible: getComputedStyle(document.getElementById('bs-owner-ok')).display !== 'none', okText: document.getElementById('bs-owner-ok').textContent.trim(), saveText: document.getElementById('bs-save').textContent.trim(), gateVisible: getComputedStyle(document.getElementById('bs-owner-gate')).display !== 'none', err: document.getElementById('bs-error').textContent.trim(), ss: Object.keys(sessionStorage) }));
  rec({ area: 'brand-modal', ctl: '作者通道 owner 口令登录', action: 'submit owner123', after: bm5, pass: bm5.okVisible && bm5.ss.includes('cp_owner_token') });
  await shot(page, 'agent1-shell-25-brand-owner-channel.png');
  await page.fill('#bs-company', 'A1 全站品牌测试-恢复中');
  await page.fill('#bs-initials', 'A9');
  await page.click('#bs-save'); await sleep(1400);
  const bm6 = await page.evaluate(async () => ({ apiCompany: (await (await fetch('/api/brand', { cache: 'no-store' })).json()).brand.company, modalOpen: document.getElementById('brand-settings').style.display !== 'none', override: localStorage.getItem('cp_brand_override') }));
  rec({ area: 'brand-modal', ctl: '保存并全站生效(owner) — 事后将恢复原状', action: 'click', after: { ...bm6, sidebarBrand: await navBrandText() }, pass: bm6.apiCompany === 'A1 全站品牌测试-恢复中' });
  await shot(page, 'agent1-shell-26-brand-owner-saved.png');
  await page.click('#btn-brand-settings'); await sleep(500);
  await page.click('#bs-reset'); await sleep(1400);
  const bm7 = await page.evaluate(async () => ({ apiCompany: (await (await fetch('/api/brand', { cache: 'no-store' })).json()).brand.company }));
  rec({ area: 'brand-modal', ctl: '恢复默认(owner→写全站出厂值)', action: 'click', after: bm7, pass: bm7.apiCompany === '李奕波个人作品矩阵' });
  await shot(page, 'agent1-shell-27-brand-owner-reset.png');
  await page.click('#brand-settings', { position: { x: 8, y: 8 } }).catch(() => { }); await sleep(400);

  /* S10: resume modal */
  await page.evaluate(() => document.getElementById('lp-resume')?.scrollIntoView({ block: 'start' })); await sleep(800);
  // non-owner first: drop owner token
  await page.evaluate(() => sessionStorage.removeItem('cp_owner_token'));
  await page.click('#btn-resume-settings'); await sleep(700);
  const rm0 = await page.evaluate(() => {
    const v = id => document.getElementById(id).value;
    return { name: v('rs-name-in'), role: v('rs-role-in'), pdf: v('rs-pdf-in'), saveText: document.getElementById('rs-save').textContent.trim(), gateVisible: getComputedStyle(document.getElementById('rs-owner-gate')).display !== 'none' };
  });
  rec({ area: 'resume-modal', ctl: '自定义材料 打开', action: 'click', after: rm0, pass: true });
  await shot(page, 'agent1-shell-28-resume-modal.png');
  await page.fill('#rs-name-in', 'A1 材料测试');
  await page.fill('#rs-role-in', '测试角色 / FDE');
  await page.fill('#rs-phone-in', '13800000000');
  await page.fill('#rs-email-in', 'a1@test.local');
  await page.fill('#rs-github-in', 'github.com/agent1-test');
  await page.fill('#rs-edu-in', '测试大学');
  await page.fill('#rs-certs-in', '测试证书A、测试证书B');
  await page.fill('#rs-education-in', '测试教育经历一行');
  await page.fill('#rs-skills-in', '测试技能|测试技能描述');
  await page.fill('#rs-projects-in', '测试项目|测试项目描述|测试标签1,测试标签2');
  await page.click('#rs-save'); await sleep(1000);
  const rm1 = await page.evaluate(() => ({ override: (localStorage.getItem('cp_resume_override') || '').slice(0, 200), rsName: document.getElementById('rs-name').textContent.trim(), modalOpen: document.getElementById('resume-settings').style.display !== 'none' }));
  rec({ area: 'resume-modal', ctl: '全部字段输入 + 保存（仅本机预览）', action: 'fill+save', after: rm1, pass: rm1.rsName === 'A1 材料测试' });
  await shot(page, 'agent1-shell-29-resume-local-saved.png');
  await page.click('#btn-resume-settings'); await sleep(500);
  await page.click('#rs-reset'); await sleep(1000);
  const rm2 = await page.evaluate(() => ({ override: localStorage.getItem('cp_resume_override'), rsName: document.getElementById('rs-name').textContent.trim() }));
  rec({ area: 'resume-modal', ctl: '恢复默认(非 owner)', action: 'click', after: rm2, pass: !rm2.override && rm2.rsName !== 'A1 材料测试' });
  await page.click('#btn-resume-settings'); await sleep(500);
  await page.fill('#rs-owner-pass', 'owner123'); await page.click('#rs-owner-login'); await sleep(1200);
  const rm3 = await page.evaluate(() => ({ okVisible: getComputedStyle(document.getElementById('rs-owner-ok')).display !== 'none', okText: document.getElementById('rs-owner-ok').textContent.trim(), saveText: document.getElementById('rs-save').textContent.trim(), err: document.getElementById('rs-error').textContent.trim() }));
  rec({ area: 'resume-modal', ctl: '作者通道 owner 口令登录(与品牌共用会话)', action: 'submit', after: rm3, pass: rm3.okVisible });
  await page.fill('#rs-name-in', 'A1 材料全站测试-恢复中');
  await page.click('#rs-save'); await sleep(1400);
  const rm4 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name, modalOpen: document.getElementById('resume-settings').style.display !== 'none' }));
  rec({ area: 'resume-modal', ctl: '保存为全站默认(owner) — 事后将恢复原状', action: 'click', after: rm4, pass: rm4.apiName === 'A1 材料全站测试-恢复中' });
  await shot(page, 'agent1-shell-30-resume-owner-saved.png');
  await page.click('#btn-resume-settings'); await sleep(500);
  await page.click('#rs-reset'); await sleep(1400);
  const rm5 = await page.evaluate(async () => ({ apiName: (await (await fetch('/api/resume', { cache: 'no-store' })).json()).resume.name }));
  rec({ area: 'resume-modal', ctl: '恢复默认(owner→写全站出厂值)', action: 'click', after: rm5, pass: rm5.apiName === '李奕波' });
  await shot(page, 'agent1-shell-31-resume-owner-reset.png');

  fs.writeFileSync(path.join(OUT, 'p2-result.json'), JSON.stringify({ base: BASE, steps, logs }, null, 2));
  const errs = logs.filter(l => l.t === 'pageerror' || (l.t === 'console' && l.type === 'error') || l.t.startsWith('http4') || l.t.startsWith('http5') || l.t === 'reqfail');
  console.log('P2 DONE. steps=' + steps.length + ' logs=' + logs.length + ' errs=' + errs.length);
  console.log(JSON.stringify(errs.slice(0, 40), null, 1).slice(0, 4000));
  await browser.close();
})().catch(e => { console.error('FATAL', e); fs.writeFileSync(path.join(OUT, 'p2-fatal.json'), JSON.stringify({ error: String(e), steps, logs }, null, 2)); process.exit(1); });