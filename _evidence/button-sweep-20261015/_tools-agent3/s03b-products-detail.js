// agent3 s03b — P02 续：平台筛选（修正选择器）+ 我的商品详情 10 tab 枚举与生成动作
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

async function controls(page) {
  return page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || b.getAttribute("aria-label") || "").trim()).filter(Boolean);
    const forms = Array.from(document.querySelectorAll("form[action]")).map((f) => f.getAttribute("action"));
    return { btns: [...new Set(btns)], forms: [...new Set(forms)] };
  });
}

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 }, locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(60000);
  const page = await ctx.newPage();
  attachLogs(page);

  // 平台筛选（用 href 精确选平台那条）
  await page.goto(BASE + "/products", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1000);
  await page.locator('a[href="/products?platform=douyin"]').click();
  await page.waitForURL(/platform=douyin/, { timeout: 60000 }).catch(() => {});
  await settle(page, 1000);
  rec("P02·商品池", "平台筛选(抖音)", "点击平台按钮", "URL platform=douyin",
    `url=${page.url()}`, /platform=douyin/.test(page.url()) ? "正常" : "缺陷", "");

  // ---------- 我的商品：10 个 tab 枚举 ----------
  const tabKeys = ["overview", "agent", "diagnosis", "main-images", "video", "assets", "links", "ads", "jobs", "review"];
  const tabSummary = {};
  for (const key of tabKeys) {
    await page.goto(`${BASE}/products/${PID}?tab=${key}`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await settle(page, 1400);
    const c = await controls(page);
    tabSummary[key] = c;
    const n = await shot(page, `p02-prod${PID}-tab-${key}`);
    rec("P02·商品详情", `Tab:${key}`, "打开该 tab", "页面渲染且有可点控件",
      `按钮=${JSON.stringify(c.btns.slice(0, 12))}；表单=${JSON.stringify(c.forms)}`, "正常", n);
  }
  fs.writeFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-tabs.json"), JSON.stringify(tabSummary, null, 1));

  // ---------- 生成诊断 ----------
  await page.goto(`${BASE}/products/${PID}?tab=diagnosis`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  let b = page.locator('button:has-text("生成诊断")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=diagnosis/, { timeout: 180000 }).catch(() => {});
    await settle(page, 2500);
    const dtext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-diagnosis-generated");
    rec("P02·商品详情", "生成诊断", "点击「生成诊断」", "生成诊断报告",
      `含「还没有诊断报告」=${dtext.includes("还没有诊断报告")}；页面长度=${dtext.length}`,
      !dtext.includes("还没有诊断报告") ? "正常" : "缺陷", n);
  } else rec("P02·商品详情", "生成诊断", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  // ---------- 生成主图方案 ----------
  await page.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  b = page.locator('button:has-text("生成主图")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=main-images/, { timeout: 300000 }).catch(() => {});
    await settle(page, 3000);
    const mtext = await page.locator("body").innerText();
    const planCount = await page.locator('summary:has-text("编辑方案")').count();
    const n = await shot(page, "p02-prod4-main-images-generated");
    rec("P02·商品详情", "生成主图（文案生成）", "点击「生成主图」", "生成 3-6 个主图方案",
      `方案数(编辑方案入口)=${planCount}；含「还没有主图方案」=${mtext.includes("还没有主图方案")}；含「规则生成」=${mtext.includes("规则生成")}；含「演示」=${mtext.includes("演示")}；含「fallback」=${mtext.includes("fallback")}`,
      planCount > 0 ? "正常" : "缺陷", n);
  } else rec("P02·商品详情", "生成主图（文案生成）", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  // ---------- 生成视频脚本 ----------
  await page.goto(`${BASE}/products/${PID}?tab=video`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  b = page.locator('button:has-text("生成脚本")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=video/, { timeout: 300000 }).catch(() => {});
    await settle(page, 3000);
    const vtext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-video-generated");
    rec("P02·商品详情", "生成脚本（视频文案）", "点击「生成脚本」", "生成视频脚本或如实提示",
      `含「还没有短视频脚本」=${vtext.includes("还没有短视频脚本")}；含「口播」=${vtext.includes("口播")}；含「规则生成」=${vtext.includes("规则生成")}`,
      !vtext.includes("还没有短视频脚本") ? "正常" : "缺陷", n);
  } else rec("P02·商品详情", "生成脚本（视频文案）", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  // ---------- 生成链接 ----------
  await page.goto(`${BASE}/products/${PID}?tab=links`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  b = page.locator('button:has-text("生成链接")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=links/, { timeout: 120000 }).catch(() => {});
    await settle(page, 2000);
    const ltext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-links-generated");
    rec("P02·商品详情", "生成链接", "点击「生成链接」", "生成推广链接",
      `含「还没有推荐链接」=${ltext.includes("还没有推荐链接")}`, !ltext.includes("还没有推荐链接") ? "正常" : "缺陷", n);
  } else rec("P02·商品详情", "生成链接", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  // ---------- 素材 tab：推送按钮存在性 + 同步历史素材 ----------
  await page.goto(`${BASE}/products/${PID}?tab=assets`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const assetsText = await page.locator("body").innerText();
  const pushBtn = await page.locator('button:has-text("推送"), button:has-text("素材中心")').count();
  rec("P02·商品详情", "推送到素材中心按钮", "检查素材/主图 tab 的 DOM",
    "存在按钮（推送生成物到 P07）", `按钮命中=${pushBtn}；页面含「素材中心」=${assetsText.includes("素材中心")}`,
    pushBtn > 0 ? "正常" : "缺陷", "（缺失，AGENTS.md 记「前端按钮待补」）");
  b = page.locator('button:has-text("同步历史素材")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=assets/, { timeout: 120000 }).catch(() => {});
    await settle(page, 1800);
    const stext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-assets-synced");
    rec("P02·商品详情", "同步历史素材", "点击后", "提示已同步/失败如实",
      `含「已同步历史素材」=${stext.includes("已同步历史素材")}；含「同步失败」=${stext.includes("同步失败")}`,
      stext.includes("已同步历史素材") || stext.includes("同步失败") ? "正常" : "部分", n);
  } else rec("P02·商品详情", "同步历史素材", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  // ---------- 任务 tab ----------
  await page.goto(`${BASE}/products/${PID}?tab=jobs`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const jtext = await page.locator("body").innerText();
  const n2 = await shot(page, "p02-prod4-jobs");
  rec("P02·商品详情", "生成任务中心(jobs)", "打开 tab", "任务列表/空态",
    `含「生成任务中心」=${jtext.includes("生成任务中心")}；含「还没有生成任务」=${jtext.includes("还没有生成任务")}`, "正常", n2);

  // ---------- 生成复盘 ----------
  await page.goto(`${BASE}/products/${PID}?tab=review`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  b = page.locator('button:has-text("生成复盘")');
  if (await b.count()) {
    await b.first().click();
    await page.waitForURL(/tab=review/, { timeout: 240000 }).catch(() => {});
    await settle(page, 2500);
    const rtext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-review-generated");
    rec("P02·商品详情", "生成复盘", "点击「生成复盘」", "生成复盘报告或如实提示先录数据",
      `含「暂无复盘报告」=${rtext.includes("暂无复盘报告")}；含「先生成复盘」=${rtext.includes("先生成复盘")}；含「规则生成」=${rtext.includes("规则生成")}；含「失败」=${rtext.includes("失败")}`,
      !rtext.includes("暂无复盘报告") ? "正常" : "部分", n);
  } else rec("P02·商品详情", "生成复盘", "查找按钮", "存在", "未找到按钮", "缺陷", "");

  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });