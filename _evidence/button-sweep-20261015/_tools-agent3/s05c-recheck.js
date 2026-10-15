// agent3 s05c — 修正复核：ads「已人工确认」徽标 + design/cs 登录（显式填表）
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

async function loginAs(page, email) {
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 600);
  await page.fill("input[name=email]", email);
  await page.fill("input[name=password]", "Test123456");
  await page.getByRole("button", { name: "登录" }).click({ noWaitAfter: true });
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 120000 });
}

(async () => {
  const browser = await launch();

  // ---- ads 徽标复核 ----
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 }, locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(60000);
  const page = await ctx.newPage();
  attachLogs(page);
  await page.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2200);
  const ads = await page.locator("body").innerText();
  const n = await shot(page, "p02-prod4-ads-confirmed-final");
  rec("P02·投放", "已人工确认徽标复核", "读 ads tab 建议卡状态徽标",
    "confirm 后显示「已人工确认」",
    `含「已人工确认」=${ads.includes("已人工确认")}；含「待人工确认」=${ads.includes("待人工确认")}；含「规则生成」=${ads.includes("规则生成")}`,
    ads.includes("已人工确认") ? "正常" : "部分", n);
  await ctx.close();

  // ---- design ----
  const ctxD = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "zh-CN" });
  ctxD.setDefaultTimeout(60000);
  const pd1 = await ctxD.newPage();
  attachLogs(pd1);
  await loginAs(pd1, "design@legacy.example.com");
  await pd1.goto(`${BASE}/products/${PID}?tab=overview`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pd1, 1500);
  const dText = await pd1.locator("body").innerText();
  const delVisible = await pd1.locator('a[href$="/delete"]:has-text("删除商品")').count();
  const nD1 = await shot(pd1, "p02-rbac-design-product-overview");
  rec("P02·RBAC", "美工打开商品详情", "design 登录并直连商品页",
    "可编辑 → 删除商品可见、无只读提示",
    `删除商品按钮=${delVisible}；含只读提示=${dText.includes("只读")}；含保存商品=${dText.includes("保存商品")}；登录邮箱正确=${dText.includes("王美工")}`,
    delVisible > 0 && !dText.includes("只读") ? "正常" : "缺陷", nD1);
  await pd1.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pd1, 2200);
  const dAds = await pd1.locator("body").innerText();
  const confirmForm = await pd1.locator('summary:has-text("人工确认建议")').count();
  const warn = dAds.includes("需要「确认投放」权限");
  const nD2 = await shot(pd1, "p02-rbac-design-ads-confirm");
  rec("P02·RBAC", "美工广告确认权限", "design 打开 ads tab",
    "无确认投放权限 → 确认表单隐藏、显示权限提示",
    `确认表单=${confirmForm}；权限提示=${warn}；确认建议按钮=${await pd1.locator('button:has-text("确认建议")').count()}`,
    confirmForm === 0 && warn ? "正常" : "缺陷", nD2);
  await ctxD.close();

  // ---- cs ----
  const ctxC = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "zh-CN" });
  ctxC.setDefaultTimeout(60000);
  const pc = await ctxC.newPage();
  attachLogs(pc);
  await loginAs(pc, "cs@legacy.example.com");
  await pc.goto(`${BASE}/products/${PID}?tab=overview`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1500);
  const cText = await pc.locator("body").innerText();
  const cDel = await pc.locator('a[href$="/delete"]:has-text("删除商品")').count();
  const nC1 = await shot(pc, "p02-rbac-cs-product-overview");
  rec("P02·RBAC", "客服打开商品详情", "cs 登录并直连商品页",
    "只读 → 写操作按钮隐藏 + 只读提示",
    `删除商品=${cDel}；含只读提示=${cText.includes("只读")}；含保存商品=${cText.includes("保存商品")}；登录身份=${cText.includes("赵客服")}`,
    cDel === 0 && cText.includes("只读") ? "正常" : "缺陷", nC1);
  await pc.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1400);
  const cMi = await pc.locator("body").innerText();
  const cGen = await pc.locator('button:has-text("生成主图")').count();
  rec("P02·RBAC", "客服主图 tab 写按钮", "cs 打开 main-images",
    "生成主图/编辑方案隐藏", `生成主图按钮=${cGen}；含「编辑方案」=${cMi.includes("编辑方案")}`,
    cGen === 0 && !cMi.includes("编辑方案") ? "正常" : "缺陷", "");
  await pc.goto(`${BASE}/products`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1400);
  const cList = await pc.locator("body").innerText();
  const cDelBtns = await pc.locator('a[href$="/delete"]').count();
  const nC2 = await shot(pc, "p02-rbac-cs-products-list");
  rec("P02·RBAC", "客服商品池列表", "cs 打开 /products",
    "行内删除按钮隐藏", `删除链接数=${cDelBtns}；列表含我的商品=${cList.includes(CREATED.productName)}`,
    cDelBtns === 0 ? "正常" : "缺陷", nC2);
  await ctxC.close();

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });