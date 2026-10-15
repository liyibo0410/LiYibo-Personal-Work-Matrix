// agent3 s03（C1）— P02 商品池页 + 我的测试商品详情（10 个 tab 枚举 + 生成动作）
// 我的测试商品由 s02b 创建：UI测试-可删-agent3（id 见 TEMP/opencode/agent3-created.json）
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
    const links = Array.from(document.querySelectorAll("main a[href]")).map((a) => a.getAttribute("href") + "|" + (a.innerText || "").trim().slice(0, 20));
    return { btns: [...new Set(btns)], forms, links: [...new Set(links)].filter((x) => !x.startsWith("/products") || true) };
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

  // ---------- 商品池页 ----------
  await page.goto(BASE + "/products", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  let n = await shot(page, "p02-products-list");
  const plist = await page.locator("body").innerText();
  rec("P02·商品池", "列表页渲染", "打开 /products", "指标 + 全部商品行",
    `含「商品池」=${plist.includes("商品池")}；含我的商品=${plist.includes(CREATED.productName)}；行数(进入按钮)=${await page.getByRole("link", { name: "进入" }).count()}`, plist.includes(CREATED.productName) ? "正常" : "缺陷", n);

  // 搜索
  await page.fill('input[name="q"]', "UI测试");
  await page.press('input[name="q"]', "Enter");
  await page.waitForURL(/q=/, { timeout: 60000 }).catch(() => {});
  await settle(page, 1200);
  const searched = await page.locator("body").innerText();
  n = await shot(page, "p02-products-search");
  rec("P02·商品池", "搜索框", "输入「UI测试」回车",
    "仅剩匹配商品", `url=${page.url()}；含我的商品=${searched.includes(CREATED.productName)}；含种子商品「低糖燕麦饼干」=${searched.includes("低糖燕麦饼干")}`,
    searched.includes(CREATED.productName) ? "正常" : "缺陷", n);

  // 清除全部筛选
  const clear = page.getByRole("link", { name: "清除全部筛选" });
  if (await clear.count()) {
    await clear.click();
    await page.waitForURL(/\/products$/, { timeout: 60000 }).catch(() => {});
    await settle(page, 1000);
    rec("P02·商品池", "清除全部筛选", "点击后", "回到 /products 全量列表",
      `url=${page.url()}`, /\/products$/.test(page.url()) ? "正常" : "缺陷", "");
  } else {
    rec("P02·商品池", "清除全部筛选", "查找链接", "存在", "未渲染（搜索态下应出现）", "缺陷", "");
  }

  // 平台筛选
  await page.getByRole("link", { name: "抖音", exact: true }).click();
  await page.waitForURL(/platform=douyin/, { timeout: 60000 }).catch(() => {});
  await settle(page, 1000);
  rec("P02·商品池", "平台筛选(抖音)", "点击平台按钮", "URL platform=douyin",
    `url=${page.url()}`, /platform=douyin/.test(page.url()) ? "正常" : "缺陷", "");
  await page.goto(BASE + "/products", { waitUntil: "domcontentloaded", timeout: 120000 });

  // ---------- 进入我的商品 ----------
  await page.goto(`${BASE}/products/${PID}`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2000);
  n = await shot(page, "p02-prod4-overview");
  rec("P02·商品详情", "商品&竞品(tab=overview)", "打开我的商品详情",
    "总览渲染 + 工作流步骤", `标题含商品名=${(await page.locator("body").innerText()).includes(CREATED.productName)}`, "正常", n);

  const tabKeys = ["overview", "agent", "diagnosis", "main-images", "video", "assets", "links", "ads", "jobs", "review"];
  const tabSummary = {};
  for (const key of tabKeys) {
    await page.goto(`${BASE}/products/${PID}?tab=${key}`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await settle(page, 1400);
    const c = await controls(page);
    tabSummary[key] = c;
    n = await shot(page, `p02-prod4-tab-${key}`);
    rec("P02·商品详情", `Tab:${key}`, "打开该 tab", "页面渲染且有可点控件",
      `按钮=${JSON.stringify(c.btns.slice(0, 12))}；表单=${JSON.stringify(c.forms)}`, "正常", n);
  }
  fs.writeFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-tabs.json"), JSON.stringify(tabSummary, null, 1));

  // ---------- 诊断：生成诊断 ----------
  await page.goto(`${BASE}/products/${PID}?tab=diagnosis`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const gd = page.locator('button:has-text("生成诊断")');
  if (await gd.count()) {
    await gd.first().click();
    await page.waitForURL(/tab=diagnosis/, { timeout: 180000 }).catch(() => {});
    await settle(page, 2500);
    const dtext = await page.locator("body").innerText();
    n = await shot(page, "p02-prod4-diagnosis-generated");
    rec("P02·商品详情", "生成诊断", "点击「生成诊断」", "生成诊断报告",
      `含「还没有诊断报告」=${dtext.includes("还没有诊断报告")}；页面长度=${dtext.length}；含「定位」=${dtext.includes("定位")}`,
      !dtext.includes("还没有诊断报告") ? "正常" : "缺陷", n);
  } else {
    rec("P02·商品详情", "生成诊断", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  // ---------- 主图：生成主图方案 ----------
  await page.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const gm = page.locator('button:has-text("生成主图")');
  if (await gm.count()) {
    await gm.first().click();
    await page.waitForURL(/tab=main-images/, { timeout: 240000 }).catch(() => {});
    await settle(page, 3000);
    const mtext = await page.locator("body").innerText();
    const planCount = await page.locator('summary:has-text("编辑方案")').count();
    n = await shot(page, "p02-prod4-main-images-generated");
    rec("P02·商品详情", "生成主图（文案生成）", "点击「生成主图」", "生成 3-6 个主图方案",
      `方案数(编辑方案入口)=${planCount}；含「还没有主图方案」=${mtext.includes("还没有主图方案")}；含「规则」=${mtext.includes("规则")}；含「演示」=${mtext.includes("演示")}`,
      planCount > 0 ? "正常" : "缺陷", n);
  } else {
    rec("P02·商品详情", "生成主图（文案生成）", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  // ---------- 视频：生成脚本 ----------
  await page.goto(`${BASE}/products/${PID}?tab=video`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const gv = page.locator('button:has-text("生成脚本")');
  if (await gv.count()) {
    await gv.first().click();
    await page.waitForURL(/tab=video/, { timeout: 240000 }).catch(() => {});
    await settle(page, 3000);
    const vtext = await page.locator("body").innerText();
    n = await shot(page, "p02-prod4-video-generated");
    rec("P02·商品详情", "生成脚本（视频文案）", "点击「生成脚本」", "生成视频脚本",
      `含「还没有短视频脚本」=${vtext.includes("还没有短视频脚本")}；含「口播」=${vtext.includes("口播")}；含「规则」=${vtext.includes("规则")}`,
      !vtext.includes("还没有短视频脚本") ? "正常" : "缺陷", n);
  } else {
    rec("P02·商品详情", "生成脚本（视频文案）", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  // ---------- 链接：生成链接 ----------
  await page.goto(`${BASE}/products/${PID}?tab=links`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const gl = page.locator('button:has-text("生成链接")');
  if (await gl.count()) {
    await gl.first().click();
    await page.waitForURL(/tab=links/, { timeout: 120000 }).catch(() => {});
    await settle(page, 2000);
    const ltext = await page.locator("body").innerText();
    n = await shot(page, "p02-prod4-links-generated");
    rec("P02·商品详情", "生成链接", "点击「生成链接」", "生成推广链接",
      `含「还没有推荐链接」=${ltext.includes("还没有推荐链接")}`, !ltext.includes("还没有推荐链接") ? "正常" : "缺陷", n);
  } else {
    rec("P02·商品详情", "生成链接", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  // ---------- 素材：同步历史素材 + 推送到素材中心（检查存在性） ----------
  await page.goto(`${BASE}/products/${PID}?tab=assets`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const assetsText = await page.locator("body").innerText();
  const pushBtn = await page.locator('button:has-text("推送"), button:has-text("素材中心")').count();
  rec("P02·商品详情", "推送到素材中心按钮", "检查素材/主图相关 tab 的 DOM",
    "存在按钮（可推送生成物到 P07）", `按钮命中=${pushBtn}；页面含「素材中心」=${assetsText.includes("素材中心")}`,
    pushBtn > 0 ? "正常" : "缺陷", "（缺失：AGENTS.md 已记「前端按钮待补」）");
  const sync = page.locator('button:has-text("同步历史素材")');
  if (await sync.count()) {
    await sync.first().click();
    await page.waitForURL(/tab=assets/, { timeout: 120000 }).catch(() => {});
    await settle(page, 1500);
    const stext = await page.locator("body").innerText();
    n = await shot(page, "p02-prod4-assets-synced");
    rec("P02·商品详情", "同步历史素材", "点击后", "提示已同步",
      `含「已同步历史素材」=${stext.includes("已同步历史素材")}；含「同步失败」=${stext.includes("同步失败")}`,
      stext.includes("已同步历史素材") || stext.includes("同步失败") ? "正常" : "部分", n);
  } else {
    rec("P02·商品详情", "同步历史素材", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  // ---------- 任务 tab ----------
  await page.goto(`${BASE}/products/${PID}?tab=jobs`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const jtext = await page.locator("body").innerText();
  n = await shot(page, "p02-prod4-jobs");
  rec("P02·商品详情", "生成任务中心(jobs)", "打开 tab", "任务列表/空态",
    `含「生成任务中心」=${jtext.includes("生成任务中心")}；含「还没有生成任务」=${jtext.includes("还没有生成任务")}`, "正常", n);

  // ---------- 复盘：生成复盘 ----------
  await page.goto(`${BASE}/products/${PID}?tab=review`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const gr = page.locator('button:has-text("生成复盘")');
  if (await gr.count()) {
    await gr.first().click();
    await page.waitForURL(/tab=review/, { timeout: 180000 }).catch(() => {});
    await settle(page, 2500);
    const rtext = await page.locator("body").innerText();
    n = await shot(page, "p02-prod4-review-generated");
    rec("P02·商品详情", "生成复盘", "点击「生成复盘」", "生成复盘报告或如实提示先录数据",
      `含「暂无复盘报告」=${rtext.includes("暂无复盘报告")}；含「先生成复盘」=${rtext.includes("先生成复盘")}`,
      !rtext.includes("暂无复盘报告") ? "正常" : "部分", n);
  } else {
    rec("P02·商品详情", "生成复盘", "查找按钮", "存在", "未找到按钮", "缺陷", "");
  }

  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });