/* agent2 wave-2 verification (2026-10-15 ~10:40+) — clean answers while tunnel healthy.
 * Wave 1 (10:27-10:31) hit a 502 flicker: P01 /api/chat showed 请求失败(HTTP 502).
 * Probes at 10:36-10:38: public+local all 200 (~13-17s). This wave re-runs the KEY flows:
 *  P01: KB-hit(怎么退款 / 退款政策) / out-of-KB refusal / chip 查订单状态 / TTS outcome
 *  P04: console 检索问答 hit + refusal with correct new-text polling
 * Public first; a failed ask retries once, then falls back to local 127.0.0.1:5173 (noted).
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const P01P = 'http://39.96.200.45:8090/p01/';
const P01L = 'http://127.0.0.1:5173';
const P04P = 'http://39.96.200.45:8090/p04/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const now = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
const steps = [];
const rec = (o) => { o.t = now(); steps.push(o); console.log('[rec] ' + JSON.stringify(o).slice(0, 480)); };
let seq = 112;
const snap = async (page, tag) => { const fn = `agent2-${++seq}-${tag}.png`; await page.screenshot({ path: path.join(OUT, fn) }); return fn; };

(async () => {
  const started = new Date();
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });
  const c1 = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const p1 = await c1.newPage();
  const chatResp = [], p1fail = [], p1con = [], ttsResp = [];
  p1.on('response', r => {
    const u = r.url();
    if (u.includes('/api/chat/tts')) ttsResp.push(`${now()} ${r.status()} ${u.slice(0, 100)}`);
    else if (u.includes('/api/chat')) chatResp.push(`${now()} ${r.status()} ${r.request().method()} ${u.slice(0, 110)}`);
  });
  p1.on('requestfailed', r => { const u = r.url(); if (u.includes('/api/chat') || u.includes('/commerce')) p1fail.push(`${now()} FAIL ${r.request().method()} ${u.slice(0, 130)} :: ${(r.failure() || {}).errorText || ''}`); });
  p1.on('console', m => { if (m.type() === 'error') p1con.push(`${now()} ${m.text().slice(0, 200)}`); });

  const errText = () => p1.evaluate(() => { const e = document.querySelector('.error-message'); return e ? e.innerText.trim() : ''; });
  const typing = () => p1.evaluate(() => !!document.querySelector('.typing-indicator'));
  const lastBot = () => p1.evaluate(() => { const b = document.querySelectorAll('.bot-bubble'); return b.length ? b[b.length - 1].innerText.trim() : ''; });
  const botCount = () => p1.$$eval('.bot-bubble', e => e.length);
  const reset = async () => { await p1.click('text=新对话'); await sleep(1200); };

  async function askOnce(page, q, timeoutMs) {
    await page.click('text=新对话'); await sleep(1200);
    const n0 = await page.$$eval('.bot-bubble', e => e.length);
    const k0 = chatResp.length;
    await page.fill('.composer input', q);
    await page.click('.composer button[type=submit]');
    const t0 = Date.now();
    while (Date.now() - t0 < timeoutMs) {
      await sleep(1500);
      const err = await page.evaluate(() => { const e = document.querySelector('.error-message'); return e ? e.innerText.trim() : ''; });
      if (err) return { ok: false, err, s: ((Date.now() - t0) / 1000).toFixed(1), net: chatResp.slice(k0).concat(p1fail.slice(-1)) };
      const n = await page.$$eval('.bot-bubble', e => e.length);
      const t = await page.evaluate(() => { const b = document.querySelectorAll('.bot-bubble'); return b.length ? b[b.length - 1].innerText.trim() : ''; });
      const ty = await page.evaluate(() => !!document.querySelector('.typing-indicator'));
      if (n > n0 && t && !ty) return { ok: true, ans: t, s: ((Date.now() - t0) / 1000).toFixed(1), net: chatResp.slice(k0) };
    }
    return { ok: false, err: 'timeout', s: ((Date.now() - t0) / 1000).toFixed(1), net: chatResp.slice(k0) };
  }

  const localTodo = [];
  async function askWithRetry(q, tag, expect) {
    let r = await askOnce(p1, q, 130000);
    if (!r.ok) {
      rec({ area: 'P01(公网)', ctl: `对话·${tag}`, action: `发送『${q}』(第1次)`, expected: expect, actual: { err: r.err, s: r.s, net: r.net }, verdict: '公网失败(重试1次)', shot: await snap(p1, `p01w-${tag}-try1-fail`) });
      await sleep(2500);
      r = await askOnce(p1, q, 130000);
      if (!r.ok) {
        rec({ area: 'P01(公网)', ctl: `对话·${tag}`, action: `发送『${q}』(第2次)`, expected: expect, actual: { err: r.err, s: r.s, net: r.net }, verdict: '公网失败→转本地', shot: await snap(p1, `p01w-${tag}-try2-fail`) });
        localTodo.push({ q, tag, expect });
        return null;
      }
    }
    rec({ area: 'P01(公网)', ctl: `对话·${tag}`, action: `发送『${q}』`, expected: expect, actual: { ok: r.ok, s: r.s, ans: (r.ans || '').slice(0, 420), net: r.net }, verdict: '正常', shot: await snap(p1, `p01w-${tag}`) });
    return r;
  }

  try {
    await p1.goto(P01P, { waitUntil: 'load', timeout: 60000 }); await sleep(5000);
    rec({ area: 'P01(公网)', ctl: '页面加载', action: 'GET /p01/', actual: { title: await p1.title(), url: p1.url() }, verdict: '正常', shot: null });

    let lastOk = await askWithRetry('怎么退款', 'kb-refund-how', '命中知识库/退款流程，无「未检索到」');
    if (lastOk) lastOk.q = '怎么退款';
    let r2 = await askWithRetry('退款政策是什么', 'kb-refund-policy', '命中知识库（退款/退货政策）');
    if (r2) lastOk = { ...r2, q: '退款政策是什么' };
    const r3 = await askWithRetry('你们公司CEO的私人手机号是多少？', 'kb-refusal', '库外：明确拒答不编造');

    // chip 查订单状态
    try {
      await p1.click('text=新对话'); await sleep(1200);
      const n0 = await botCount();
      const k0 = chatResp.length;
      await p1.click(".welcome-chip:has-text('查订单状态')");
      const t0 = Date.now(); let done = null;
      while (Date.now() - t0 < 130000) {
        await sleep(1500);
        const err = await errText();
        if (err) { done = { err }; break; }
        const n = await botCount(); const t = await lastBot(); const ty = await typing();
        if (n > n0 && t && !ty) { done = { ans: t }; break; }
      }
      rec({ area: 'P01(公网)', ctl: '按钮·快捷chip「查订单状态」', action: '点击', expected: '发送并回答（真实订单状态）', actual: { s: ((Date.now() - t0) / 1000).toFixed(1), ...(done || { err: 'timeout' }), net: chatResp.slice(k0) }, verdict: done && done.ans ? '正常' : '缺陷/公网失败', shot: await snap(p1, 'p01w-chip-order') });
    } catch (e) { rec({ area: 'P01(公网)', ctl: '按钮·快捷chip「查订单状态」', action: '点击', actual: '异常: ' + String(e).slice(0, 150), verdict: '缺陷', shot: null }); }

    // TTS outcome（用最后一个气泡的喇叭）
    try {
      await sleep(500);
      const btns = await p1.$$('.tts-button');
      if (btns.length) {
        await btns[btns.length - 1].click();
        const t0 = Date.now();
        let cls = '';
        while (Date.now() - t0 < 26000) {
          await sleep(2000);
          cls = await btns[btns.length - 1].evaluate(e => e.className + '|disabled=' + e.disabled);
          if (ttsResp.length) break;
        }
        rec({ area: 'P01(公网)', ctl: '按钮·语音播报', action: '点击后观察 ≤26s', expected: '成功播放或可见失败提示', actual: { cls, ttsResp: ttsResp.slice(-3) }, verdict: ttsResp.some(x => x.includes('200')) ? '正常' : '缺陷(复现)', shot: await snap(p1, 'p01w-tts') });
      } else {
        rec({ area: 'P01(公网)', ctl: '按钮·语音播报', action: '点击', actual: '未测：无按钮', verdict: '未测', shot: null });
      }
    } catch (e) { rec({ area: 'P01(公网)', ctl: '按钮·语音播报', action: '点击', actual: '异常: ' + String(e).slice(0, 150), verdict: '缺陷', shot: null }); }

    /* 本地兜底（仅公网失败的问题） */
    if (localTodo.length) {
      rec({ area: 'P01(本地)', ctl: '兜底说明', action: '-', actual: `下列问题公网 2 次失败，转本地 127.0.0.1:5173 复测: ${localTodo.map(x => x.q).join(' / ')}`, verdict: '信息', shot: null });
      await p1.goto(P01L, { waitUntil: 'load', timeout: 45000 }); await sleep(5000);
      for (const item of localTodo) {
        const r = await askOnce(p1, item.q, 130000);
        rec({ area: 'P01(本地)', ctl: `对话·${item.tag}`, action: `发送『${item.q}』`, expected: item.expect, actual: { ok: r.ok, err: r.err, s: r.s, ans: (r.ans || '').slice(0, 420) }, verdict: r.ok ? '正常(本地)' : '缺陷/失败', shot: await snap(p1, `p01wL-${item.tag}`) });
      }
    }
  } catch (e) {
    rec({ area: 'P01', ctl: '整段', action: '-', actual: 'FATAL: ' + String(e).slice(0, 250), verdict: '缺陷', shot: null });
  }
  const p01ChatNet = chatResp.slice(); const p01Fails = p1fail.slice();
  await c1.close();

  /* ─────────── P04 console QA (proper new-text polling) ─────────── */
  const c2 = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const p2 = await c2.newPage();
  const p2net = [], p2con = [];
  p2.on('response', r => { if (r.status() >= 400) p2net.push(`${now()} ${r.status()} ${r.request().method()} ${r.url().slice(0, 150)}`); });
  p2.on('requestfailed', r => { if (!r.url().includes('/stream/')) p2net.push(`${now()} FAIL ${r.url().slice(0, 150)}`); });
  p2.on('console', m => { if (m.type() === 'error') p2con.push(`${now()} ${m.text().slice(0, 200)}`); });

  async function qaConsole(q, tag, timeoutMs = 260000) {
    await p2.click('.nav-item[data-tab="tab-qa"]'); await sleep(1500);
    const txt0 = await p2.innerText('#qaThread').catch(() => '');
    await p2.fill('#qaInput', q);
    if (await p2.$('#qaSend')) await p2.click('#qaSend'); else await p2.click("button:has-text('发送')");
    const t0 = Date.now(); let newTxt = '';
    while (Date.now() - t0 < timeoutMs) {
      await sleep(3000);
      const txt = await p2.innerText('#qaThread').catch(() => '');
      newTxt = txt.startsWith(txt0) ? txt.slice(txt0.length) : txt;
      const tail = newTxt.slice(-260);
      if (newTxt.length > 10 && !/正在思考|等待中|进行中/.test(tail) && /引用来源|未记载|未找到|库内无此产品|无法提供|未收录|抱歉/.test(newTxt)) break;
    }
    return { newTxt, s: ((Date.now() - t0) / 1000).toFixed(0) };
  }

  try {
    await p2.goto(P04P, { waitUntil: 'load', timeout: 60000 }); await sleep(4500);
    const land = await p2.evaluate(() => ({ url: location.href, title: document.title }));
    rec({ area: 'P04(公网)', ctl: '入口', action: 'GET /p04/', actual: land, verdict: /console\.html/.test(land.url) ? '正常' : '部分', shot: null });
    // 重新检查按钮
    try {
      const hb0 = await p2.innerText('#healthSummary').catch(() => '');
      const btn = await p2.$("button:has-text('重新检查')");
      if (btn) { await btn.click(); await sleep(4000); }
      const hb1 = await p2.innerText('#healthSummary').catch(() => '');
      rec({ area: 'P04(公网)', ctl: '按钮·重新检查', action: '点击', expected: '重新探活', actual: { before: hb0.slice(0, 80), after: hb1.slice(0, 80) }, verdict: hb1 ? '正常' : '部分', shot: await snap(p2, 'p04w-health') });
    } catch (e) { rec({ area: 'P04(公网)', ctl: '按钮·重新检查', action: '点击', actual: '异常: ' + String(e).slice(0, 150), verdict: '缺陷', shot: null }); }

    const qa1 = await qaConsole('H3C LA2608 交换机的交换容量是多少？', 'hit');
    const qaOk = /引用来源/.test(qa1.newTxt);
    rec({ area: 'P04(公网)', ctl: '检索问答·库内命中(复验)', action: '提问交换容量', expected: '答案 + 引用来源', actual: { s: qa1.s, hasSrc: qaOk, tail: qa1.newTxt.slice(0, 600).replace(/\n/g, ' ') }, verdict: qaOk ? '正常' : '缺陷', shot: await snap(p2, 'p04w-qa-hit') });

    const qa2 = await qaConsole('请告诉我 iPhone 17 Pro Max 的电池容量是多少', 'refusal');
    const refused = /未记载|未找到|库内无此产品|无法提供|未收录|抱歉/.test(qa2.newTxt);
    rec({ area: 'P04(公网)', ctl: '检索问答·库外拒答(复验)', action: '提问 iPhone 电池容量', expected: '明确拒答', actual: { s: qa2.s, refused, text: qa2.newTxt.slice(0, 600).replace(/\n/g, ' ') }, verdict: refused ? '正常' : '缺陷', shot: await snap(p2, 'p04w-qa-refusal') });
  } catch (e) {
    rec({ area: 'P04', ctl: '整段', action: '-', actual: 'FATAL: ' + String(e).slice(0, 250), verdict: '缺陷', shot: null });
  }
  await c2.close();

  const out = {
    started: started.toISOString(), finished: new Date().toISOString(),
    startedLocal: started.toLocaleString('zh-CN'), finishedLocal: new Date().toLocaleString('zh-CN'),
    steps, p01_chat_network: p01ChatNet, p01_request_failed: p01Fails, p01_tts_responses: ttsResp,
    p01_console: p1con, p04_net4xx5xx: p2net, p04_console: p2con,
  };
  fs.writeFileSync(path.join(OUT, 'agent2-p01p04-verify-wave2-20261015.json'), JSON.stringify(out, null, 1), 'utf-8');
  console.log('WAVE2 DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });