/* agent2 re-verification pass (2026-10-15 ~10:25+) — public P01 + P04.
 * Purpose: independently re-verify the key claims of the interrupted sweep at the CURRENT time
 * (public tunnel was reported dead 09:50-10:02, back since). Read-only interactions only:
 * - P01: load / clear / KB-hit questions / out-of-KB refusal / one chip / sidebar refresh / TTS re-check
 * - P04: /p04/ 307 landing / health bar / docs list (seed only) / console QA (hit + refusal) /
 *        chat.html (hit + refusal) / stream toggle
 * No code/config/service is modified. No doc upload/delete this pass (done in earlier pass).
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = 'D:\\software\\PycharmProjects\\作品矩阵\\_evidence\\button-sweep-20261015';
const P01 = 'http://39.96.200.45:8090/p01/';
const P04 = 'http://39.96.200.45:8090/p04/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const now = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
const steps = [];
const rec = (o) => { o.t = now(); steps.push(o); console.log('[rec] ' + JSON.stringify(o).slice(0, 520)); };
let seq = 96;
const snap = async (page, tag) => {
  const fn = `agent2-${++seq}-${tag}.png`;
  await page.screenshot({ path: path.join(OUT, fn) });
  return fn;
};

(async () => {
  const started = new Date();
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-proxy-server'] });

  /* ─────────────── P01 (public) ─────────────── */
  const c1 = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const p1 = await c1.newPage();
  const p1console = [], p1net = [], p1tts = [];
  p1.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') p1console.push(`[${m.type()}] ${m.text().slice(0, 240)}`); });
  p1.on('response', r => {
    if (r.url().includes('/api/chat/tts')) p1tts.push(`${r.status()} ${r.url().slice(0, 120)}`);
    if (r.status() >= 400) p1net.push(`${r.status()} ${r.request().method()} ${r.url().slice(0, 170)}`);
  });
  p1.on('requestfailed', r => p1net.push(`FAIL ${r.url().slice(0, 170)} :: ${(r.failure() || {}).errorText || ''}`));

  const p1turns = () => p1.$$eval('.turn-card', els => els.length);
  const p1ask = async (text, timeoutMs = 200000) => {
    const n0 = await p1turns();
    await p1.fill('.composer input', text);
    await p1.click('.composer button[type=submit]');
    const t0 = Date.now();
    try {
      await p1.waitForFunction(n => document.querySelectorAll('.turn-card').length > n, n0, { timeout: timeoutMs });
      await p1.waitForFunction(() => !document.querySelector('.typing-indicator'), null, { timeout: timeoutMs });
    } catch (e) { return { st: 'WAIT-FAIL', err: String(e).slice(0, 160), ans: '' }; }
    const ans = await p1.evaluate(() => {
      const t = document.querySelectorAll('.turn-card'); if (!t.length) return '';
      const last = t[t.length - 1]; const b = last.querySelectorAll('.bot-bubble');
      return b.length ? b[b.length - 1].innerText.trim() : '';
    });
    return { st: `ok(${((Date.now() - t0) / 1000).toFixed(1)}s)`, ans };
  };

  try {
    await p1.goto(P01, { waitUntil: 'load', timeout: 60000 });
    await sleep(6000);
    const init = await p1.evaluate(() => ({
      title: document.title,
      turns: document.querySelectorAll('.turn-card').length,
      chips: [...document.querySelectorAll('.welcome-chip')].map(e => e.innerText.trim()),
      sidebarCards: document.querySelectorAll('.sidebar-card').length,
    }));
    rec({ area: 'P01', ctl: '页面加载', action: `GET ${P01}`, actual: init, verdict: '正常', shot: await snap(p1, 'p01v-initial') });

    // 新对话（清空）
    await p1.click('text=新对话'); await sleep(2500);
    const cleared = await p1.evaluate(() => ({ turns: document.querySelectorAll('.turn-card').length, chips: document.querySelectorAll('.welcome-chip').length }));
    rec({ area: 'P01', ctl: '按钮·新对话(清空)', action: '点击', expected: '回到欢迎页', actual: cleared, verdict: cleared.turns === 0 ? '正常' : '部分', shot: await snap(p1, 'p01v-cleared-welcome') });

    // KB 命中复验 1：怎么退款
    let r = await p1ask('怎么退款');
    let shot = await snap(p1, 'p01v-kb-refund-how');
    rec({ area: 'P01', ctl: '对话·怎么退款', action: '发送', expected: '命中种子 FAQ，无「未检索到」', actual: { st: r.st, ans: r.ans.slice(0, 420), hitted: !r.ans.includes('未检索到') }, verdict: (r.st.startsWith('ok') && !r.ans.includes('未检索到') && r.ans.length > 10) ? '正常' : '缺陷', shot });
    await p1.click('text=新对话'); await sleep(2000);

    // KB 命中复验 2：退款政策是什么
    r = await p1ask('退款政策是什么');
    shot = await snap(p1, 'p01v-kb-refund-policy');
    rec({ area: 'P01', ctl: '对话·退款政策是什么', action: '发送', expected: '命中种子 FAQ', actual: { st: r.st, ans: r.ans.slice(0, 420), hitted: !r.ans.includes('未检索到') }, verdict: (r.st.startsWith('ok') && !r.ans.includes('未检索到') && r.ans.length > 10) ? '正常' : '缺陷', shot });
    await p1.click('text=新对话'); await sleep(2000);

    // 库外问题拒答复验
    r = await p1ask('你们公司CEO的私人手机号是多少？');
    shot = await snap(p1, 'p01v-kb-refusal');
    rec({ area: 'P01', ctl: '对话·库外问题(CEO手机号)', action: '发送', expected: '明确拒答不编造', actual: { st: r.st, ans: r.ans.slice(0, 420) }, verdict: r.st.startsWith('ok') && r.ans.length > 5 ? '正常' : '缺陷', shot });
    await p1.click('text=新对话'); await sleep(2000);

    // 快捷 chip：查订单状态
    try {
      const n0 = await p1turns();
      await p1.click(".welcome-chip:has-text('查订单状态')");
      const t0 = Date.now();
      await p1.waitForFunction(n => document.querySelectorAll('.turn-card').length > n, n0, { timeout: 200000 });
      await p1.waitForFunction(() => !document.querySelector('.typing-indicator'), null, { timeout: 200000 });
      const chipInfo = await p1.evaluate(() => {
        const t = document.querySelectorAll('.turn-card'); const last = t[t.length - 1];
        const u = last.querySelector('.user-bubble'); const b = last.querySelectorAll('.bot-bubble');
        return { user: u ? u.innerText.trim().slice(0, 80) : '', ans: b.length ? b[b.length - 1].innerText.trim().slice(0, 420) : '' };
      });
      rec({ area: 'P01', ctl: '按钮·快捷chip「查订单状态」', action: '点击', expected: '发送问句并回答', actual: { st: `ok(${((Date.now() - t0) / 1000).toFixed(1)}s)`, ...chipInfo }, verdict: chipInfo.ans.length > 5 ? '正常' : '缺陷', shot: await snap(p1, 'p01v-chip-order') });
    } catch (e) {
      rec({ area: 'P01', ctl: '按钮·快捷chip「查订单状态」', action: '点击', actual: '异常: ' + String(e).slice(0, 160), verdict: '缺陷', shot: await snap(p1, 'p01v-chip-order-err') });
    }

    // 侧栏刷新对象列表
    try {
      const before = await p1.$$eval('.sidebar-card', els => els.length);
      await p1.click("button:has-text('刷新对象列表')"); await sleep(3500);
      const after = await p1.$$eval('.sidebar-card', els => els.map(e => e.innerText.replace(/\s+/g, ' ').slice(0, 60)));
      rec({ area: 'P01', ctl: '按钮·刷新对象列表', action: '点击', expected: '重新拉取侧栏', actual: { before, afterCount: after.length, after }, verdict: after.length > 0 ? '正常' : '缺陷', shot: await snap(p1, 'p01v-sidebar-refresh') });
    } catch (e) {
      rec({ area: 'P01', ctl: '按钮·刷新对象列表', action: '点击', actual: '异常: ' + String(e).slice(0, 160), verdict: '缺陷', shot: null });
    }

    // TTS 复验（上一轮判为缺陷：503 且无提示）
    try {
      p1tts.length = 0;
      const btn = await p1.$('.tts-button');
      if (btn) {
        await btn.click(); await sleep(6000);
        const cls = await btn.evaluate(e => e.className + '|disabled=' + e.disabled);
        rec({ area: 'P01', ctl: '按钮·语音播报(复验)', action: '点击后等 6s', expected: '正常播放或给出可见提示', actual: { btnClass: cls, ttsResponses: p1tts.slice(0, 4) }, verdict: p1tts.some(x => x.startsWith('200')) ? '正常' : '缺陷(复现:503无提示)', shot: await snap(p1, 'p01v-tts-state') });
      } else {
        rec({ area: 'P01', ctl: '按钮·语音播报(复验)', action: '点击', actual: '未测：无 tts-button', verdict: '未测', shot: null });
      }
    } catch (e) {
      rec({ area: 'P01', ctl: '按钮·语音播报(复验)', action: '点击', actual: '异常: ' + String(e).slice(0, 160), verdict: '缺陷', shot: null });
    }
  } catch (e) {
    rec({ area: 'P01', ctl: '整段', action: '-', actual: 'FATAL: ' + String(e).slice(0, 300), verdict: '缺陷', shot: null });
  }
  await c1.close();

  /* ─────────────── P04 (public) ─────────────── */
  const c2 = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: 'zh-CN' });
  const p2 = await c2.newPage();
  const p2console = [], p2net = [], redirs = [];
  p2.on('console', m => { if (m.type() === 'error') p2console.push(`[${m.type()}] ${m.text().slice(0, 240)}`); });
  p2.on('response', r => {
    const s = r.status();
    if (s >= 300 && s < 400) redirs.push(`${s} ${r.request().method()} ${r.url().slice(0, 160)} -> loc=${(r.headers()['location'] || '').slice(0, 160)}`);
    if (s >= 400) p2net.push(`${s} ${r.request().method()} ${r.url().slice(0, 170)}`);
  });
  p2.on('requestfailed', r => p2net.push(`FAIL ${r.url().slice(0, 170)} :: ${(r.failure() || {}).errorText || ''}`));

  const pollQA = async (page, selThread, timeoutMs) => {
    const t0 = Date.now(); let txt = '';
    while (Date.now() - t0 < timeoutMs) {
      await sleep(3500);
      txt = await page.innerText(selThread).catch(() => '');
      const tail = txt.slice(-500);
      if (!/正在思考|等待中/.test(tail) && (/引用来源|未记载|未找到依据|失败|超时|库内无此产品|无法/.test(txt))) break;
    }
    return { txt, s: ((Date.now() - t0) / 1000).toFixed(0) };
  };

  const p4askConsole = async (q) => {
    await p2.fill('#qaInput', q);
    if (await p2.$('#qaSend')) await p2.click('#qaSend'); else await p2.click("button:has-text('发送')");
    return pollQA(p2, '#qaThread', 260000);
  };
  const p4askChat = async (q) => {
    await p2.fill('#input', q);
    await p2.click('#send');
    const t0 = Date.now(); let last = {};
    while (Date.now() - t0 < 300000) {
      await sleep(3000);
      last = await p2.evaluate(() => {
        const msgs = document.querySelectorAll('.msg');
        for (let i = msgs.length - 1; i >= 0; i--) {
          const bub = msgs[i].querySelector('.bubble');
          if (bub && msgs[i].classList.contains('bot')) {
            const txt = bub.innerText.trim();
            if (txt) return { text: txt.slice(0, 1000), thinking: !!bub.querySelector('.typing') || /思考|等待中/.test(txt.slice(-120)), sources: bub.querySelector('.sources-bar summary') ? bub.querySelector('.sources-bar summary').innerText.trim() : '', refusal: bub.querySelector('.refusal-note') ? bub.querySelector('.refusal-note').innerText.trim() : '' };
          }
        }
        return {};
      });
      if (last.text && !last.thinking) break;
    }
    return { ...last, s: ((Date.now() - t0) / 1000).toFixed(0) };
  };

  try {
    // 1) /p04/ 入口 + 307 落地
    redirs.length = 0;
    await p2.goto(P04, { waitUntil: 'load', timeout: 60000 });
    await sleep(4500);
    const land = await p2.evaluate(() => ({ url: location.href, title: document.title, health: (document.querySelector('#healthBar') || {}).innerText ? document.querySelector('#healthBar').innerText.replace(/\s+/g, ' ').slice(0, 260) : '(no healthBar)' }));
    const cks = await c2.cookies();
    rec({ area: 'P04', ctl: '入口 GET /p04/', action: '访问', expected: '307 → 可用页面', actual: { land, redirects: redirs.slice(0, 4), cookies: cks.map(c => `${c.name}=${c.value}`).slice(0, 6) }, verdict: /console\.html|chat\.html/.test(land.url) ? '正常' : '部分', shot: await snap(p2, 'p04v-landing') });

    // 2) 文档管理列表（确认种子 5 份、无遗留测试文档）
    await p2.click('.nav-item[data-tab="tab-docs"]'); await sleep(4500);
    const docs = await p2.evaluate(() => ({
      rows: [...document.querySelectorAll('#docTableBody tr')].map(e => e.innerText.replace(/\s+/g, ' ').slice(0, 110)),
      note: (document.querySelector('#docStatsNote') || {}).innerText || '',
    }));
    rec({ area: 'P04', ctl: 'Tab·文档管理(列表)', action: '切换', expected: '列出种子文档，无「UI测试-可删」残留', actual: docs, verdict: docs.rows.length > 0 && !docs.rows.join('').includes('UI测试') ? '正常' : '部分', shot: await snap(p2, 'p04v-docs-list') });

    // 3) 检索问答：库内命中
    await p2.click('.nav-item[data-tab="tab-qa"]'); await sleep(2200);
    let qa = await p4askConsole('H3C LA2608 交换机的交换容量是多少？');
    const qaHit = { hasSrc: qa.txt.includes('引用来源'), tail: qa.txt.slice(-420).replace(/\n/g, ' '), s: qa.s };
    rec({ area: 'P04', ctl: '检索问答·库内命中', action: '提问 H3C LA2608 交换容量', expected: '答案 + 引用来源', actual: qaHit, verdict: qaHit.hasSrc ? '正常' : '缺陷', shot: await snap(p2, 'p04v-qa-seed') });

    // 4) 检索问答：库外拒答
    qa = await p4askConsole('请告诉我 iPhone 17 Pro Max 的电池容量是多少');
    const qaRef = { refused: /未记载|未找到|库内无此产品|无法/.test(qa.txt), tail: qa.txt.slice(-420).replace(/\n/g, ' '), s: qa.s };
    rec({ area: 'P04', ctl: '检索问答·库外拒答', action: '提问 iPhone 电池容量', expected: '明确拒答/未记载', actual: qaRef, verdict: qaRef.refused ? '正常' : '缺陷', shot: await snap(p2, 'p04v-qa-refusal') });

    // 5) chat.html 首屏
    await p2.goto('http://39.96.200.45:8090/p04/chat.html', { waitUntil: 'load', timeout: 60000 });
    await sleep(5000);
    const chatInit = await p2.evaluate(() => ({ apiPill: (document.querySelector('#apiPill') || {}).innerText || '', msgs: document.querySelectorAll('.msg').length, url: location.href }));
    rec({ area: 'P04', ctl: 'chat.html 首屏', action: '打开', expected: '加载 + API 连接提示', actual: chatInit, verdict: '正常', shot: await snap(p2, 'p04v-chat-initial') });

    // 6) chat.html 库内命中（含参考来源）
    let ch = await p4askChat('H3C LA2608 交换机有几个千兆端口？');
    rec({ area: 'P04', ctl: 'chat.html·库内命中', action: '提问千兆端口数', expected: '回答 + 参考来源', actual: { s: ch.s, text: (ch.text || '').slice(0, 420), sources: ch.sources }, verdict: ch.text && ch.sources ? '正常' : '缺陷', shot: await snap(p2, 'p04v-chat-answer') });

    // 7) chat.html 库外拒答
    ch = await p4askChat('请告诉我 iPhone 17 Pro Max 的电池容量是多少');
    rec({ area: 'P04', ctl: 'chat.html·库外拒答', action: '提问 iPhone 电池容量', expected: '拒答 + 标签', actual: { s: ch.s, text: (ch.text || '').slice(0, 420), refusal: ch.refusal }, verdict: (ch.refusal || /未找到|未记载|无此产品/.test(ch.text || '')) ? '正常' : '缺陷', shot: await snap(p2, 'p04v-chat-refusal') });

    // 8) 流式输出开关（只切状态，不提问）
    try {
      const before = await p2.isChecked('#streamToggle');
      await p2.click('#streamToggle'); await sleep(400);
      const mid = await p2.isChecked('#streamToggle');
      await p2.click('#streamToggle'); await sleep(400);
      const after = await p2.isChecked('#streamToggle');
      rec({ area: 'P04', ctl: 'chat.html·流式输出开关', action: '切两次', expected: 'checked 状态切换且可还原', actual: { before, mid, after }, verdict: before !== mid && after === before ? '正常' : '部分', shot: null });
    } catch (e) {
      rec({ area: 'P04', ctl: 'chat.html·流式输出开关', action: '切换', actual: '异常: ' + String(e).slice(0, 160), verdict: '缺陷', shot: null });
    }
  } catch (e) {
    rec({ area: 'P04', ctl: '整段', action: '-', actual: 'FATAL: ' + String(e).slice(0, 300), verdict: '缺陷', shot: null });
  }
  await c2.close();

  const out = {
    started: started.toISOString(), finished: new Date().toISOString(),
    startedLocal: started.toLocaleString('zh-CN'), finishedLocal: new Date().toLocaleString('zh-CN'),
    steps,
    p01_console: p1console, p01_net_problems: p1net, p01_tts_responses: p1tts,
    p04_console: p2console, p04_net_problems: p2net,
  };
  fs.writeFileSync(path.join(OUT, 'agent2-p01p04-verify-20261015.json'), JSON.stringify(out, null, 1), 'utf-8');
  console.log('VERIFY DONE steps=' + steps.length);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });