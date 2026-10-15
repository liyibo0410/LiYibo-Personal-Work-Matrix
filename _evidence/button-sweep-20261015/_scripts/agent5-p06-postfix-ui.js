/* P06 修复后 UI 复验：数据表「查看」逐行点击（修复前同款操作）+ 首屏 sanity */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const EVID = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1560, height: 950 } })).newPage();
  page.setDefaultTimeout(20000);
  const api = [];
  page.on('response', r => { if (r.url().includes('/api/v1/')) api.push(`${r.status()} ${r.url().split('/api/v1/')[1]}`); });
  const res = { ts: new Date().toISOString(), dash: null, rows: [], ok: 0, fail: [] };
  try {
    await page.goto('http://127.0.0.1:8060/', { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(2500);
    res.dash = await page.evaluate(() => ({ badge: (document.getElementById('dash-badge') || {}).textContent || '', stats: document.querySelectorAll('#dash-stats .stat-card').length }));
    await page.click('.nav-item[data-page="tables"]');
    await page.waitForFunction(() => document.querySelectorAll('#tables-table tbody tr').length >= 5, null, { timeout: 30000 });
    const n = await page.$$eval('#tables-table tbody tr', t => t.length);
    let shot = false;
    for (let i = 1; i <= n; i++) {
      const tname = await page.$eval(`#tables-table tbody tr:nth-child(${i}) td`, td => td.innerText);
      let opened = false, err = '';
      for (let a = 1; a <= 2 && !opened; a++) {
        const idx = api.length;
        try {
          await page.click(`#tables-table tbody tr:nth-child(${i}) button`);
          await page.waitForFunction(() => { const d = document.getElementById('table-detail'); return d && d.style.display !== 'none' && document.querySelectorAll('#detail-preview-body tr').length > 0; }, null, { timeout: 8000 });
          opened = true;
          const title = await page.$eval('#detail-title', el => el.innerText);
          res.rows.push({ t: tname, v: 'ok', attempt: a, title });
          if (!shot) { shot = true; await page.screenshot({ path: path.join(EVID, 'agent5-95-p06-postfix-table-detail.png'), timeout: 20000, animations: 'disabled' }).catch(() => { }); }
          await page.click('#table-detail button', { timeout: 4000 }).catch(() => { });
          await page.waitForFunction(() => document.getElementById('table-detail').style.display === 'none', null, { timeout: 4000 }).catch(() => { });
        } catch (e) {
          err += `A${a}[${e.message.split('\n')[0].slice(0, 40)}; ${api.slice(idx).filter(x => x.includes('/tables/' + tname)).join(',')}] `;
          await page.click('#table-detail button', { timeout: 1200 }).catch(() => { });
          await page.waitForTimeout(250);
        }
      }
      if (opened) res.ok++; else { res.fail.push(tname); res.rows.push({ t: tname, v: 'fail', detail: err }); }
    }
    res.summary = `成功 ${res.ok}/${n}；失败 ${res.fail.length}`;
  } catch (e) { res.error = e.message.slice(0, 200); }
  fs.writeFileSync(path.join(EVID, 'agent5-p06-postfix-ui.json'), JSON.stringify(res, null, 2), 'utf-8');
  console.log(JSON.stringify({ dash: res.dash, summary: res.summary || res.error, fails: res.fail }));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });