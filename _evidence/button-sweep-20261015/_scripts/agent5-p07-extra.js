/* P07 补充控件：卡片点击进详情 / 返回素材库 / 报表行点击（全部只读） */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const EVID = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const P7B = process.env.P7E_BASE || 'http://39.96.200.45:8090/p07/';
const P7T = process.env.P7E_TAG || 'public';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1560, height: 950 } })).newPage();
  page.setDefaultTimeout(30000);
  const steps = [];
  const rec = (w, a, e, act, v) => { steps.push({ ts: new Date().toISOString(), base: P7B, w, a, e, act: String(act).slice(0, 400), v }); console.log(`[${v}] ${w} | ${act.slice(0, 140)}`); };
  try {
    await page.goto(P7B, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(1500);
    await page.click('#nav .tab[data-page="library"]');
    await page.waitForSelector('#asset-grid .card', { timeout: 30000 });
    const firstId = await page.evaluate(() => { const c = document.querySelector('#asset-grid .card'); c.click(); return 'clicked'; });
    await page.waitForFunction(() => document.body.innerText.includes('素材信息'), null, { timeout: 30000 });
    await page.waitForTimeout(800);
    const detail = await page.evaluate(() => ({ hash: location.hash, hasBack: !!Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('返回素材库')) }));
    rec('素材库卡片点击', '点击第一张素材卡', '进入详情', `hash=${detail.hash}；返回按钮=${detail.hasBack}`, detail.hash.startsWith('#asset/') ? '正常' : '缺陷');
    await page.screenshot({ path: path.join(EVID, `agent5-90-p07-${P7T}-card-click-detail.png`), timeout: 20000, animations: 'disabled' }).catch(() => { });

    await page.click('button:has-text("← 返回素材库")');
    await page.waitForSelector('#kw', { timeout: 20000 });
    rec('返回素材库', '点击「← 返回素材库」', '回到素材库网格', '素材库表单可见', '正常');

    await page.click('#nav .tab[data-page="report"]');
    await page.waitForSelector('#content table tbody tr', { timeout: 60000 });
    await page.click('#content table tbody tr');
    await page.waitForFunction(() => document.body.innerText.includes('素材信息'), null, { timeout: 30000 });
    const d2 = await page.evaluate(() => ({ hash: location.hash }));
    rec('效果关联行点击', '点击报表第一行', '进入该素材详情', `hash=${d2.hash}`, d2.hash.startsWith('#asset/') ? '正常' : '缺陷');
  } catch (e) {
    rec('补充控件', '脚本异常', '-', e.message.slice(0, 200), '缺陷');
  }
  fs.writeFileSync(path.join(EVID, `agent5-p07-${P7T}-extra.json`), JSON.stringify({ ts: new Date().toISOString(), base: P7B, steps }, null, 2), 'utf-8');
  await browser.close();
  console.log('EXTRA DONE');
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });