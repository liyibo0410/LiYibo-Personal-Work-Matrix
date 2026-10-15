/* 监督窗口验证脚本 v2（只读）：P05 TDZ 修复 + 外壳 127.0.0.1 挂载修复
 * 用法（在 _tools-agent1 目录下，含 playwright 依赖）：
 *   node _verify-fixes.js
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const out = { ts: new Date().toISOString() };

  // ① P05：修复前 cfxEnter() 在 const CFX_* 之前调用 → TDZ → window.CR 永不赋值
  {
    const p = await browser.newPage();
    const errs = [];
    p.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
    p.on('console', (m) => { if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 140)); });
    await p.goto('http://127.0.0.1:8770/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await p.waitForTimeout(1200);
    out.p05Login = {
      CR: await p.evaluate(() => typeof window.CR),
      errors: errs.slice(0, 6),
      roles: await p.locator('.role-item').count(),
    };
    // 登录 admin（演示角色点击即入）
    await p.locator('.role-item[data-role="admin"]').click();
    await p.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 15000 }).catch(() => {});
    await p.waitForTimeout(800);
    out.p05AfterLogin = { url: p.url() };
    // 逐页检查四个曾被 TDZ 打死的页面（同一 page 顺序导航，Cookies 保持）
    out.p05Pages = {};
    const pageSpecs = [
      ['workbench(/)', '/', "() => ({CR: typeof CR, textLen: document.body.innerText.length})"],
      ['rules(/rules)', '/rules', "() => ({CR: typeof CR, typeList: (document.getElementById('typeList')||{innerHTML:''}).innerHTML.length, textLen: document.body.innerText.length})"],
      ['twin(/twin)', '/twin', "() => ({CR: typeof CR, textLen: document.body.innerText.length})"],
    ];
    for (const [name, path, probe] of pageSpecs) {
      const before = errs.length;
      await p.goto('http://127.0.0.1:8770' + path, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await p.waitForTimeout(2200);
      out.p05Pages[name] = { ...(await p.evaluate(eval(probe))), newErrors: errs.slice(before, before + 4), url: p.url() };
    }
    await p.close();
  }

  // ② 外壳：修复前 127.0.0.1 被判为非本机 → 挂载 iframe 指向公网隧道 URL
  //    改为真实登录（owner/owner123）→ 深链 #/workspace/data-platform → 读 #module-frame 的 src
  {
    const p = await browser.newPage();
    const errs = [];
    p.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
    await p.goto('http://127.0.0.1:8800/', { waitUntil: 'load', timeout: 30000 });
    // 登录模态默认隐藏：先点「登录进入演示」打开（cta-demo 兜底）
    await p.click('#btn-login-open').catch(() => p.click('#cta-demo'));
    await p.waitForTimeout(600);
    await p.fill('#login-user', 'owner');
    await p.fill('#login-pass', 'owner123');
    await p.click('#login-btn');
    await p.waitForTimeout(2500);
    const loggedIn = await p.evaluate(() => !!(document.querySelector('#app-view') || {}).classList && !document.querySelector('#app-view').classList.contains('cp-hidden'));
    await p.goto('http://127.0.0.1:8800/#/workspace/data-platform', { waitUntil: 'load', timeout: 30000 });
    await p.waitForTimeout(3500);
    const src = await p.getAttribute('#module-frame', 'src').catch(() => null);
    out.shell = {
      loggedIn,
      moduleFrameSrc: src,
      expectLocal: 'http://127.0.0.1:8060',
      errors: errs.slice(0, 6),
    };
    await p.close();
  }

  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});