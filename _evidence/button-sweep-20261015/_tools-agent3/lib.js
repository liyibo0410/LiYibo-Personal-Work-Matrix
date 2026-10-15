// agent3 sweep library — Playwright (system Chrome, headless, --no-proxy-server).
// 只测不改：不触碰仓库代码/配置/服务；证据落 _evidence/button-sweep-20261015/。
// 复用 agent1 的 node_modules（避免重复装包）。
"use strict";
const path = require("path");
const fs = require("fs");

const PW = require(path.join(__dirname, "..", "_tools-agent1", "node_modules", "playwright"));
const EV = path.join(__dirname, "..");           // _evidence/button-sweep-20261015
const TMP = path.join(process.env.TEMP || "", "opencode");
fs.mkdirSync(TMP, { recursive: true });

// ---- 序号管理：从现有 agent3-<n>- 文件名里找最大值 +1，避免与既有截图撞号 ----
function nextShotNumber() {
  let max = 0;
  for (const f of fs.readdirSync(EV)) {
    const m = f.match(/^agent3-(\d{1,3})-/);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  for (const f of fs.readdirSync(EV)) {
    const m = f.match(/^agent3b-(\d{1,3})-/);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  const stPath = path.join(__dirname, "state.json");
  let st = { seq: max };
  try { st = JSON.parse(fs.readFileSync(stPath, "utf-8")); } catch (e) {}
  st.seq = Math.max(st.seq || 0, max) + 1;
  fs.writeFileSync(stPath, JSON.stringify(st));
  return st.seq;
}

function shot(page, desc, full = false) {
  const n = nextShotNumber();
  const safe = String(desc).replace(/[^\w\u4e00-\u9fa5-]+/g, "-").slice(0, 60);
  const fn = `agent3-${String(n).padStart(3, "0")}-${safe}.png`;
  return page.screenshot({ path: path.join(EV, fn), fullPage: full }).then(() => fn);
}

// ---- 行记录：JSONL（供报告统计）+ stdout ----
const ROWS = path.join(__dirname, "rows.jsonl");
function rec(pageTag, control, action, expected, actual, verdict, evidence = "") {
  const row = {
    t: new Date().toISOString().slice(11, 19),
    page: pageTag, control, action,
    expected: String(expected).slice(0, 400),
    actual: String(actual).slice(0, 700),
    verdict, evidence,
  };
  fs.appendFileSync(ROWS, JSON.stringify(row) + "\n");
  console.log(`[${verdict}] ${pageTag} | ${control} | ${String(actual).slice(0, 200)}`);
}

async function launch() {
  const browser = await PW.chromium.launch({
    channel: "chrome",
    headless: true,
    args: ["--no-proxy-server", "--disable-background-networking", "--mute-audio"],
  });
  return browser;
}

async function newPage(browser, viewport = { width: 1500, height: 950 }) {
  const ctx = await browser.newContext({ viewport, locale: "zh-CN", timezoneId: "Asia/Shanghai" });
  ctx.setDefaultTimeout(45000);
  const page = await ctx.newPage();
  attachLogs(page);
  return { ctx, page };
}

function attachLogs(page) {
  page._console = [];
  page._net4xx = [];
  page._netfail = [];
  page.on("console", (m) => { if (m.type() === "error") page._console.push(m.text()); });
  page.on("response", (r) => { if (r.status() >= 400) page._net4xx.push(`${r.status()} ${r.request().method()} ${r.url()}`); });
  page.on("requestfailed", (r) => page._netfail.push(`${r.method()} ${r.url()} :: ${(r.failure() || {}).errorText || ""}`));
}

function issues(page) {
  return { console: page._console.slice(-12), http4xx: page._net4xx.slice(-12), failed: page._netfail.slice(-12) };
}

async function settle(page, ms = 800) {
  try { await page.waitForLoadState("networkidle", { timeout: 12000 }); } catch (e) {}
  await page.waitForTimeout(ms);
}

module.exports = { PW, EV, TMP, launch, newPage, shot, rec, issues, settle, attachLogs, nextShotNumber };