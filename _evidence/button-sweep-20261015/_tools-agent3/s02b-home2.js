// agent3 s02b — P02 工作台续：新建店铺 / 新建商品 / 经营总览标注 / 模型配置(boss)
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const PROD = "UI测试-可删-agent3";
const STORE = "UI测试-可删-店铺";

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 }, locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(45000);
  const page = await ctx.newPage();
  attachLogs(page);

  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2000);

  // ---------- 新建店铺 ----------
  const storeAlready = (await page.locator("body").innerText()).includes(STORE);
  if (!storeAlready) {
    await page.locator('form[action="/stores/create"] input[name=name]').fill(STORE);
    await page.locator('form[action="/stores/create"] input[name=owner_name]').fill("测试负责人");
    await page.locator('form[action="/stores/create"] button[type=submit]').click();
    await page.waitForURL(`${BASE}/`, { timeout: 60000 }).catch(() => {});
    await settle(page, 1800);
  }
  const storeInfo = await page.evaluate((name) => {
    const card = Array.from(document.querySelectorAll("div")).find((d) => {
      const t = d.textContent || "";
      return t.includes(name) && d.querySelector('form[action*="/delete"]');
    });
    const form = card ? card.querySelector('form[action*="/delete"]') : null;
    return { cardFound: !!card, action: form ? form.getAttribute("action") : "" };
  }, STORE);
  let n = await shot(page, "p02-home-store-created");
  rec("P02·工作台", "新建店铺", `创建「${STORE}」`, "店铺卡出现在店铺视图",
    `卡片出现=${storeInfo.cardFound}；删除表单action=${storeInfo.action}`, storeInfo.cardFound ? "正常" : "缺陷", n);

  // ---------- 新建商品 ----------
  const prodAlready = (await page.locator("body").innerText()).includes(PROD);
  if (!prodAlready) {
    await page.locator('form[action="/products/create"] input[name=name]').fill(PROD);
    await page.locator('form[action="/products/create"] input[name=category]').fill("测试类目");
    await page.locator('form[action="/products/create"] input[name=price]').fill("9.9");
    await page.locator('form[action="/products/create"] textarea[name=selling_points]').fill("测试卖点A，测试卖点B");
    await page.locator('form[action="/products/create"] button[type=submit]').click();
    await page.waitForURL(`${BASE}/`, { timeout: 60000 }).catch(() => {});
    await settle(page, 1800);
  }
  const prodInfo = await page.evaluate((name) => {
    const link = Array.from(document.querySelectorAll("a")).find(
      (a) => /\/products\/\d+$/.test(a.getAttribute("href") || "") && a.closest("div")?.parentElement?.textContent?.includes(name));
    const del = Array.from(document.querySelectorAll("a")).find(
      (a) => /\/products\/\d+\/delete$/.test(a.getAttribute("href") || "") && a.getAttribute("aria-label")?.includes(name));
    return { detail: link ? link.getAttribute("href") : "", del: del ? del.getAttribute("href") : "" };
  }, PROD);
  n = await shot(page, "p02-home-product-created");
  rec("P02·工作台", "新建商品", `创建「${PROD}」`, "商品出现在商品池且带详情/删除入口",
    `详情=${prodInfo.detail}；删除入口=${prodInfo.del}`, prodInfo.detail ? (prodInfo.del ? "正常" : "部分") : "缺陷", n);
  fs.writeFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"),
    JSON.stringify({ productName: PROD, productHref: prodInfo.detail, storeName: STORE, storeAction: storeInfo.action }));

  // ---------- 经营总览 ----------
  await page.goto(BASE + "/dashboard", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const dash = await page.locator("body").innerText();
  const live = dash.includes("数据来源：P06 数据中台（实时）");
  const degraded = dash.includes("已降级");
  n = await shot(page, "p02-dashboard-boss");
  rec("P02·经营总览", "P06 指标来源标注", "老板打开 /dashboard",
    "显示 metrics_source 标注（实时 或 降级）",
    `实时徽标=${live}；降级徽标=${degraded}；含「跨模块调用失败」=${dash.includes("跨模块调用失败")}；含「暂无 P06 指标数据」=${dash.includes("暂无 P06 指标数据")}`,
    live || degraded ? "正常" : "缺陷", n);

  // ---------- 模型配置(boss) ----------
  await page.goto(BASE + "/settings", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const st = await page.locator("body").innerText();
  n = await shot(page, "p02-settings-boss");
  const hasErr = st.includes("模型配置读取失败");
  rec("P02·模型配置", "页面渲染(老板)", "老板打开 /settings",
    "三模型状态卡 + 配置表单", `含「模型配置中心」=${st.includes("模型配置中心")}；读取失败=${hasErr}；测试按钮数=${await page.getByRole("button", { name: /测试/ }).count()}；用户区块=${st.includes("成员") || st.includes("用户")}`,
    !hasErr && st.includes("模型配置中心") ? "正常" : "缺陷", n);

  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });