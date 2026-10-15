/* 监督窗口验证：P03 健康徽标（2.10）+ 会话持久化（2.12）
 * 手法：initScript 预置 sessionStorage 会话 → 加载页面 → 断言恢复渲染 + 徽标在位 + 零报错。
 * 输出：console + 同目录 UTF-8 JSON 证据文件。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SEED = {
  messages: [
    { role: 'user', content: 'PERSIST-SMOKE 用户消息' },
    { role: 'ai', content: 'PERSIST-SMOKE AI 回复' },
  ],
  threadId: 'smoke-thread-20261015',
};

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await browser.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e.message).slice(0, 220)));
  p.on('console', (m) => {
    if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 220));
  });

  await p.addInitScript((seed) => {
    try {
      sessionStorage.setItem('p03-chat-session-v1', JSON.stringify(seed));
    } catch (e) {}
  }, SEED);

  await p
    .goto('http://127.0.0.1:5174/', { waitUntil: 'load', timeout: 30000 })
    .catch((e) => errs.push('goto ' + e.message));
  await p.waitForTimeout(4500);

  const out = await p.evaluate(() => {
    const txt = document.body.innerText || '';
    const badge = document.querySelector('.health-badge');
    let stored = null;
    try {
      stored = JSON.parse(sessionStorage.getItem('p03-chat-session-v1') || 'null');
    } catch (e) {}
    return {
      restoredUser: txt.includes('PERSIST-SMOKE 用户消息'),
      restoredAi: txt.includes('PERSIST-SMOKE AI 回复'),
      threadKept: !!(stored && stored.threadId === 'smoke-thread-20261015'),
      msgCountAfterLoad: Array.isArray(stored && stored.messages) ? stored.messages.length : -1,
      badge: badge
        ? { text: badge.textContent.trim(), cls: badge.className, title: badge.getAttribute('title') }
        : null,
      viteOverlay: !!document.querySelector('vite-error-overlay'),
    };
  });
  out.errors = errs.slice(0, 8);
  out.ts = new Date().toISOString();

  const outFile = path.join(__dirname, '..', '监督验证-P03-徽标与会话持久化-20261015.json');
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2), 'utf8');
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL', e.message);
  process.exit(1);
});
