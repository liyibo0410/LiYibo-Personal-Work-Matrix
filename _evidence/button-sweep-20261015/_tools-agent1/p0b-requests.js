/* Trace all network requests on the landing page to locate the 404. */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const BASE = process.env.SHELL_BASE || 'http://39.96.200.45:8070';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();
  const reqs = [];
  page.on('request', r => reqs.push({ phase: 'req', url: r.url(), rt: r.resourceType() }));
  page.on('response', r => reqs.push({ phase: 'resp', url: r.url(), status: r.status() }));
  page.on('requestfailed', r => reqs.push({ phase: 'fail', url: r.url(), err: (r.failure() || {}).errorText }));
  await page.goto(BASE + '/', { waitUntil: 'load', timeout: 45000 }).catch(e => reqs.push({ phase: 'gotoerr', err: String(e).slice(0, 200) }));
  await page.waitForTimeout(4000);
  fs.writeFileSync(path.join(OUT, 'p0b-requests.json'), JSON.stringify(reqs, null, 2));
  const bad = reqs.filter(x => (x.phase === 'resp' && x.status >= 400) || x.phase === 'fail');
  console.log('BAD n=' + bad.length);
  for (const b of bad) console.log(b.phase, b.status || '', b.url, b.err || '');
  console.log('ALL n=' + reqs.length);
  for (const r of reqs) console.log(r.phase, r.status || '', (r.url || '').slice(0, 140));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });