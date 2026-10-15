/* agent2 wave-3 micro-probe (2026-10-15 ~10:52+)
 * 1) P04: browser double-fetch of /documents & /search — is the list still browser-cached? (D1)
 * 2) P01: click 刷新对象列表 on public — does it re-fetch and keep/clear cards, any error text? (wave1 ambiguity)
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const now = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
const steps = [];
const rec = (o) => { o.t = now(); steps.push(o); console.log('[rec] ' + JSON.stringify(o).slice(0, 520)); };
let seq = 122;
const snap = async (page, tag) => { const fn = `agent2-${++seq}-${tag}.png`; await page.screenshot({ path: path.join(OUT, fn) }); return fn; };

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });

  /* P04 cache probe */
  const c2 = await browser.newContext({ viewport: { width: 1400, height: 900 }, locale: 'zh-CN' });
  const p2 = await c2.newPage();
  const respLog = [];
  p2.on('response', r => { if (/\/documents|\/search/.test(r.url())) respLog.push(`${now()} ${r.status()} ${r.url().slice(0, 120)}`); });
  try {
    await p2.goto('http://39.96.200.45:8090/p04/', { waitUntil: 'load', timeout: 60000 }); await sleep(4000);
    const probe = await p2.evaluate(async () => {
      const out = [];
      for (const url of ['/documents', '/search?keyword=test']) {
        for (let i = 0; i < 2; i++) {
          const t0 = performance.now();
          const r = await fetch(url, { headers: { 'x-probe': 'agent2' } });
          await r.text();
          const t1 = performance.now();
          const entries = performance.getEntriesByName(location.origin + url);
          const last = entries[entries.length - 1] || {};
          out.push({ url, round: i + 1, status: r.status, cc: r.headers.get('cache-control'), ms: Math.round(t1 - t0), transferSize: last.transferSize, duration: last.duration ? Math.round(last.duration) : null });
        }
      }
      return out;
    });
    rec({ area: 'P04', ctl: '列表接口缓存复验(浏览器内双发)', action: 'fetch ×2', expected: '第二轮仍真实回源（no-store）', actual: probe, verdict: probe.every(x => x.cc === 'no-store') ? '正常(已修复)' : '需复核', shot: null });
  } catch (e) { rec({ area: 'P04', ctl: '缓存复验', action: 'fetch', actual: '异常: ' + String(e).slice(0, 200), verdict: '缺陷', shot: null }); }
  await c2.close();

  /* P01 sidebar refresh probe */
  const c1 = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const p1 = await c1.newPage();
  const net = [];
  p1.on('response', r => { if (r.url().includes('/commerce')) net.push(`${now()} ${r.status()} ${r.url().slice(0, 110)}`); });
  p1.on('requestfailed', r => { if (r.url().includes('/commerce')) net.push(`${now()} FAIL ${r.url().slice(0, 110)}`); });
  try {
    await p1.goto('http://39.96.200.45:8090/p01/', { waitUntil: 'load', timeout: 60000 }); await sleep(6000);
    const before = await p1.$$eval('.sidebar-card', e => e.length);
    net.length = 0;
    await p1.click("button:has-text('刷新对象列表')"); await sleep(5000);
    const st = await p1.evaluate(() => ({
      cards: document.querySelectorAll('.sidebar-card').length,
      err: (() => { const e = document.querySelector('.sidebar-error'); return e ? e.innerText.trim() : '(no .sidebar-error)'; })(),
      btn: (() => { const b = [...document.querySelectorAll('button')].find(x => /刷新对象列表|加载中/.test(x.innerText)); return b ? b.innerText.trim() : '?'; })(),
    }));
    rec({ area: 'P01', ctl: '按钮·刷新对象列表(复验)', action: '点击', expected: '重新拉 orders+products', actual: { before, ...st, net: net.slice(0, 6) }, verdict: st.cards > 0 && !/失败/.test(st.err) ? '正常' : '部分', shot: await snap(p1, 'p01w-sidebar-refresh2') });
  } catch (e) { rec({ area: 'P01', ctl: '刷新对象列表(复验)', action: '点击', actual: '异常: ' + String(e).slice(0, 200), verdict: '缺陷', shot: null }); }
  await c1.close();

  const out = { startedLocal: new Date().toLocaleString('zh-CN'), steps };
  fs.writeFileSync(path.join(OUT, 'agent2-p01p04-verify-wave3-20261015.json'), JSON.stringify(out, null, 1), 'utf-8');
  console.log('WAVE3 DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });