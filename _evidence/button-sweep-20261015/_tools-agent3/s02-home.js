// agent3 s02 — P02 工作台（首页）：四图表 / 刷新 / 演示数据 / 下载模板 / 平台筛选 / 建店铺 / 建商品 / 经营总览 / 模型配置(boss)
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs, PW } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const PROD = "UI测试-可删-agent3";
const STORE = "UI测试-可删-店铺";

async function chartProbe(page) {
  return page.evaluate(() => {
    const out = [];
    const cards = Array.from(document.querySelectorAll("section > div")).filter((d) =>
      d.querySelector("canvas"));
    // 简单起见：全页面所有 canvas + 最近的标题卡片文本
    for (const c of Array.from(document.querySelectorAll("canvas"))) {
      const card = c.closest("div");
      let title = "";
      let p = c.parentElement;
      for (let i = 0; i < 10 && p; i++) {
        const t = p.querySelector("h3, h2");
        if (t && t.textContent.trim()) { title = t.textContent.trim(); break; }
        p = p.parentElement;
      }
      let ink = 0, colors = new Set();
      try {
        const ctx = c.getContext("2d");
        const w = c.width, h = c.height;
        const img = ctx.getImageData(0, 0, w, h).data;
        const step = Math.max(4, Math.floor(Math.sqrt((w * h) / 4000)));
        for (let y = 0; y < h; y += step) {
          for (let x = 0; x < w; x += step) {
            const i = (y * w + x) * 4;
            const key = `${img[i]},${img[i + 1]},${img[i + 2]},${img[i + 3]}`;
            colors.add(key);
            if (img[i + 3] > 0 && !(img[i] > 248 && img[i + 1] > 248 && img[i + 2] > 248)) ink++;
          }
        }
      } catch (e) { /* ignore */ }
      out.push({ title, w: c.width, h: c.height, inkPixels: ink, distinctColors: colors.size });
    }
    return out;
  });
}

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 },
    locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(45000);
  const page = await ctx.newPage();
  attachLogs(page);
  const downloads = [];
  page.on("download", async (d) => {
    try {
      const p = path.join(process.env.TEMP || "", "opencode", `agent3-dl-${Date.now()}-${d.suggested_filename}`);
      await d.saveAs(p);
      downloads.push({ name: d.suggested_filename, bytes: fs.statSync(p).size });
    } catch (e) { downloads.push({ name: d.suggested_filename, error: String(e).slice(0, 120) }); }
  });

  // ---------- 1. 工作台 + 四图表 ----------
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2500);
  let charts = await chartProbe(page);
  let n = await shot(page, "p02-home-charts", true);
  rec("P02·工作台", "四张图表渲染", "打开首页等待 ECharts 渲染",
    "平台商品分布/店铺状态分布/各店铺商品数/商品类目分布 4 张图非空白",
    `canvas 数=${charts.length}；` + charts.map((c) => `${c.title || "?"}(${c.w}x${c.h}, 非白像素=${c.inkPixels}, 色数=${c.distinctColors})`).join(" | "),
    charts.length >= 4 && charts.every((c) => c.inkPixels > 30 && c.distinctColors > 2) ? "正常" : "缺陷", n);

  // ---------- 2. 刷新（重新加载）后图表仍在 ----------
  await page.reload({ waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2500);
  charts = await chartProbe(page);
  n = await shot(page, "p02-home-charts-after-reload");
  rec("P02·工作台", "刷新后图表", "整页 reload 后再查 canvas",
    "4 张图仍渲染（曾出过空白）",
    `canvas 数=${charts.length}；` + charts.map((c) => `${c.title || "?"}(非白=${c.inkPixels})`).join(" | "),
    charts.length >= 4 && charts.every((c) => c.inkPixels > 30) ? "正常" : "缺陷", n);

  // ---------- 3. 生成演示数据 ----------
  const demoBtn = page.getByRole("button", { name: /生成演示数据/ });
  let demoText = "";
  if (await demoBtn.count()) {
    await demoBtn.click();
    await page.waitForURL(/demo=/, { timeout: 60000 }).catch(() => {});
    await settle(page, 1200);
    demoText = (await page.locator("body").innerText()).match(/演示数据[^\n]*/)?.[0] || "";
    n = await shot(page, "p02-home-demo-data");
  }
  rec("P02·工作台", "生成演示数据按钮", "点击「生成演示数据」",
    "幂等：已存在则返回现有数据并提示", `url=${page.url()}；提示=${demoText}`, demoText ? "正常" : "部分", n);

  // ---------- 4. 下载导入模板 ----------
  const dlBefore = downloads.length;
  const dlLink = page.getByRole("link", { name: /下载导入模板/ });
  const dlCount = await dlLink.count();
  if (dlCount) {
    await dlLink.click();
    await page.waitForTimeout(2500);
  }
  const dl = downloads.slice(dlBefore);
  rec("P02·工作台", "下载导入模板", "点击链接",
    "下载 CSV 模板", `下载事件=${JSON.stringify(dl)}`, dl.length && dl[0].bytes > 100 ? "正常" : (dlCount ? "缺陷" : "未测"), "");

  // ---------- 5. 平台筛选 ----------
  await page.getByRole("link", { name: "抖音", exact: true }).click();
  await page.waitForURL(/platform=douyin/, { timeout: 60000 }).catch(() => {});
  await settle(page, 1200);
  const cntText = await page.locator("body").innerText();
  const tagMatch = cntText.match(/(\d+) \/ (\d+)/);
  n = await shot(page, "p02-home-platform-filter");
  rec("P02·工作台", "平台筛选(抖音)", "点击平台按钮「抖音」",
    "URL 带 platform=douyin，商品列表被过滤",
    `url=${page.url()}；计数=${tagMatch ? tagMatch[0] : "?"}`, /platform=douyin/.test(page.url()) ? "正常" : "缺陷", n);
  await page.getByRole("link", { name: "全部", exact: true }).click();
  await settle(page, 800);

  // ---------- 6. 新建店铺（自建自删） ----------
  await page.locator('form[action="/stores/create"] input[name=name]').fill(STORE);
  await page.locator('form[action="/stores/create"] button[type=submit]').click();
  await page.waitForURL(`${BASE}/`, { timeout: 60000 }).catch(() => {});
  await settle(page, 1500);
  const storeLink = await page.evaluate((name) => {
    const cards = Array.from(document.querySelectorAll("a")).filter((a) => a.href.includes("/stores/") && a.textContent.includes(name));
    const del = Array.from(document.querySelectorAll("a")).filter((a) => /\/stores\/\d+\/delete/.test(a.getAttribute("href") || ""));
    const cardDiv = Array.from(document.querySelectorAll("div")).find((d) => d.textContent.includes(name));
    return { storeHref: cards[0]?.getAttribute("href") || "", deleteHrefs: del.map((a) => a.getAttribute("href")) };
  }, STORE);
  n = await shot(page, "p02-home-store-created");
  rec("P02·工作台", "新建店铺", `创建「${STORE}」`,
    "店铺出现在店铺视图", `店铺链接=${storeLink.storeHref}；页面含店名=${(await page.locator("body").innerText()).includes(STORE)}`,
    storeLink.storeHref ? "正常" : "缺陷", n);

  // ---------- 7. 新建商品（自建自删） ----------
  await page.locator('form[action="/products/create"] input[name=name]').fill(PROD);
  await page.locator('form[action="/products/create"] input[name=category]').fill("测试类目");
  await page.locator('form[action="/products/create"] input[name=price]').fill("9.9");
  await page.locator('form[action="/products/create"] textarea[name=selling_points]').fill("测试卖点A，测试卖点B");
  await page.locator('form[action="/products/create"] button[type=submit]').click();
  await page.waitForURL(`${BASE}/`, { timeout: 60000 }).catch(() => {});
  await settle(page, 1500);
  const prodId = await page.evaluate((name) => {
    const as = Array.from(document.querySelectorAll("a"));
    const hit = as.find((a) => /\/products\/\d+$/.test(a.getAttribute("href") || "") && a.closest("div")?.parentElement?.textContent?.includes(name));
    if (hit) return hit.getAttribute("href");
    const row = Array.from(document.querySelectorAll("div")).find((d) => d.textContent.trim().startsWith(name));
    return "";
  }, PROD);
  n = await shot(page, "p02-home-product-created");
  rec("P02·工作台", "新建商品", `创建「${PROD}」`,
    "商品出现在商品池列表", `详情链接=${prodId}；页面含商品名=${(await page.locator("body").innerText()).includes(PROD)}`,
    prodId ? "正常" : "部分", n);
  fs.writeFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), JSON.stringify({ productName: PROD, productHref: prodId, storeName: STORE }));

  // ---------- 8. 经营总览（metrics_source 标注） ----------
  await page.goto(BASE + "/dashboard", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const dash = await page.locator("body").innerText();
  const live = dash.includes("数据来源：P06 数据中台（实时）");
  const degraded = dash.includes("已降级");
  n = await shot(page, "p02-dashboard-boss");
  rec("P02·经营总览", "P06 指标来源标注", "老板打开 /dashboard",
    "显示 metrics_source 标注（实时 或 降级）",
    `实时徽标=${live}；降级徽标=${degraded}；含 metrics_error=${dash.includes("跨模块调用失败")}；指标卡数=${await page.locator(".grid .rounded-lg").count()}`,
    live || degraded ? "正常" : "缺陷", n);

  // ---------- 9. 模型配置（boss） ----------
  await page.goto(BASE + "/settings", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const st = await page.locator("body").innerText();
  n = await shot(page, "p02-settings-boss");
  const hasErr = st.includes("模型配置读取失败");
  rec("P02·模型配置", "页面(老板)", "老板打开 /settings",
    "三模型状态卡 + 配置表单渲染", `含「模型配置中心」=${st.includes("模型配置中心")}；含读取失败=${hasErr}；含「用户」管理=${st.includes("用户")}；含「测试」按钮=${await page.getByRole("button", { name: /测试/ }).count()}`,
    !hasErr && st.includes("模型配置中心") ? "正常" : "缺陷", n);

  console.log("DOWNLOADS:", JSON.stringify(downloads));
  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });