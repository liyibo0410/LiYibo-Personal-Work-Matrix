/* agent2 wave-3b (2026-10-15 ~10:53+) — P01 sidebar refresh retry: public once, else local. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const now = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
const steps = [];
const rec = (o) => { o.t = now(); steps.push(o); console.log('[rec] ' + JSON.stringify(o).slice(0, 500)); };
let seq = 124;
const snap = async (page, tag) => { const fn = `agent2-${++seq}-${tag}.png`; await page.screenshot({ path: path.join(OUT, fn) }); return fn; };

async function probeSidebar(page, area, base) {
  const net = [];
  page.removeAllListeners('response');
  page.on('response', r => { if (r.url().includes('/commerce')) net.push(`${now()} ${r.status()} ${r.url().slice(0, 110)}`); });
  page.on('requestfailed', r => { if (r.url().includes('/commerce')) net.push(`${now()} FAIL ${r.url().slice(0, 110)}`); });
  await page.goto(base, { waitUntil: 'load', timeout: 45000 });
  await sleep(6000);
  const before = await page.$$eval('.sidebar-card', e => e.length);
  net.length = 0;
  await page.click("button:has-text('刷新对象列表')"); await sleep(5000);
  const st = await page.evaluate(() => ({
    cards: document.querySelectorAll('.sidebar-card').length,
    err: (() => { const e = document.querySelector('.sidebar-error'); return e ? e.innerText.trim() : ''; })(),
  }));
  rec({ area, ctl: '按钮·刷新对象列表', action: '点击', expected: '重新拉 orders+products', actual: { before, ...st, net: net.slice(0, 6) }, verdict: st.cards > 0 && !/失败/.test(st.err) ? '正常' : '部分', shot: await snap(page, `${area === 'P01(公网)' ? 'p01w' : 'p01wL'}-sidebar-refresh2`) });
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  try {
    await probeSidebar(page, 'P01(公网)', 'http://39.96.200.45:8090/p01/');
  } catch (e) {
    rec({ area: 'P01(公网)', ctl: '页面加载(重试)', action: 'goto', actual: '仍失败: ' + String(e).slice(0, 160), verdict: '公网不可达→转本地', shot: null });
    try {
      await probeSidebar(page, 'P01(本地)', 'http://127.0.0.1:5173');
    } catch (e2) {
      rec({ area: 'P01(本地)', ctl: '页面加载', action: 'goto', actual: '异常: ' + String(e2).slice(0, 160), verdict: '缺陷', shot: null });
    }
  }
  fs.writeFileSync(path.join(OUT, 'agent2-p01p04-verify-wave3b-20261015.json'), JSON.stringify({ startedLocal: new Date().toLocaleString('zh-CN'), steps }, null, 1), 'utf-8');
  console.log('WAVE3B DONE');
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });