/* 监督窗口验证：P01 TTS 失败可见提示 —— Playwright 拦截 /api/chat/tts 模拟厂商故障，
 * 断言点击播报后出现红字「播报失败」提示 + 按钮进入 error 态（可重试）。 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await browser.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e.message).slice(0, 200)));
  p.on('console', (m) => {
    if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 200));
  });

  // 模拟 TTS 厂商/后端故障
  await p.route('**/api/chat/tts', (r) => r.abort());

  await p.goto('http://127.0.0.1:5173/', { waitUntil: 'load', timeout: 40000 }).catch((e) => errs.push('goto ' + e.message));
  await p.waitForTimeout(2500);

  // 发一条消息拿机器人回复（真实后端 LLM）
  const inputSel = 'textarea';
  await p.fill(inputSel, '你好').catch((e) => errs.push('fill ' + e.message.slice(0, 80)));
  await p.keyboard.press('Enter').catch((e) => errs.push('enter ' + e.message.slice(0, 80)));

  await p.waitForSelector('.tts-button', { timeout: 90000 }).catch((e) => errs.push('no-tts-button'));
  const before = await p.evaluate(() => document.querySelectorAll('.tts-button').length);

  await p.click('.tts-button').catch((e) => errs.push('click ' + e.message.slice(0, 80)));
  await p.waitForTimeout(1500);

  const out = await p.evaluate(() => {
    const hint = document.querySelector('.tts-error-hint');
    const btn = document.querySelector('.tts-button.tts-error');
    return {
      ttsButtons: document.querySelectorAll('.tts-button').length,
      hintVisible: !!hint && hint.offsetParent !== null,
      hintText: hint ? hint.textContent.trim() : null,
      btnErrorClass: !!btn,
      btnTitle: btn ? btn.getAttribute('title') : null,
    };
  });
  console.log(JSON.stringify({ before, ...out, errors: errs.slice(0, 6) }, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});
