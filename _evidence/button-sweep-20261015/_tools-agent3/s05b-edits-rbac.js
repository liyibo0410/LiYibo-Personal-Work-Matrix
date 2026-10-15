// agent3 s05b — P02 续：诊断编辑 + 已确认建议复核 + RBAC(design/cs)
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const API = "http://127.0.0.1:8000";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

async function tokenFor(email) {
  const r = await fetch(API + "/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: "Test123456" }),
  });
  return (await r.json()).access_token;
}

(async () => {
  const browser = await launch();

  // ================== 老板：诊断编辑 + ads 复核 ==================
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 }, locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(60000);
  const page = await ctx.newPage();
  attachLogs(page);

  await page.goto(`${BASE}/products/${PID}?tab=diagnosis`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1300);
  const dsummary = page.locator('summary:has-text("编辑诊断")');
  if (await dsummary.count()) {
    await dsummary.first().click();
    await settle(page, 500);
    const pos = page.locator('form[action*="/diagnoses/"] textarea[name="positioning"], form[action*="/diagnoses/"] input[name="positioning"]').first();
    await pos.fill("UI测试诊断编辑：定位建议改为测试用文本");
    await page.locator('button:has-text("保存诊断")').first().click({ noWaitAfter: true });
    await page.waitForTimeout(4000);
    const dtext = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-diagnosis-edit-save");
    rec("P02·商品详情", "诊断编辑保存", "改「定位判断」后点「保存诊断」",
      "保存生效或给出失败提示",
      `url=${page.url()}；页面含「UI测试诊断编辑」=${dtext.includes("UI测试诊断编辑")}；含「失败」=${dtext.includes("失败")}`,
      dtext.includes("UI测试诊断编辑") ? "正常" : "缺陷", n);
  } else rec("P02·商品详情", "诊断编辑保存", "查找", "存在", "未找到", "未测", "");

  await page.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2200);
  const ads = await page.locator("body").innerText();
  const badge = ads.match(/(待确认|已确认|暂不采纳|已驳回|规则生成|LLM 生成)/g);
  const n2 = await shot(page, "p02-prod4-ads-confirmed-recheck");
  rec("P02·投放", "已确认建议态复核", "重开 ads tab 读徽标",
    "确认后的建议显示已确认", `命中徽标=${JSON.stringify([...new Set(badge || [])])}`,
    (badge || []).includes("已确认") ? "正常" : "部分", n2);
  await ctx.close();

  // ================== design ==================
  const ctxD = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "zh-CN" });
  ctxD.setDefaultTimeout(60000);
  const pd1 = await ctxD.newPage();
  attachLogs(pd1);
  await pd1.goto(`${BASE}/login?demo=design`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pd1, 400);
  await pd1.getByRole("button", { name: "登录" }).click();
  await pd1.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 120000 });
  await pd1.goto(`${BASE}/products/${PID}?tab=overview`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pd1, 1500);
  const dText = await pd1.locator("body").innerText();
  const delVisible = await pd1.locator('a[href$="/delete"]:has-text("删除商品")').count();
  const nD1 = await shot(pd1, "p02-rbac-design-product-overview");
  rec("P02·RBAC", "美工打开商品详情", "design 登录并直连商品页",
    "可编辑 → 删除商品可见、无只读提示",
    `删除商品按钮=${delVisible}；含只读提示=${dText.includes("只读")}；含保存商品=${dText.includes("保存商品")}`,
    delVisible > 0 && !dText.includes("只读") ? "正常" : "缺陷", nD1);
  await pd1.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pd1, 2000);
  const dAds = await pd1.locator("body").innerText();
  const confirmForm = await pd1.locator('summary:has-text("人工确认建议")').count();
  const warn = dAds.includes("需要「确认投放」权限");
  const nD2 = await shot(pd1, "p02-rbac-design-ads-confirm");
  rec("P02·RBAC", "美工广告确认权限", "design 打开 ads tab",
    "无确认投放权限 → 确认表单隐藏、显示权限提示",
    `确认表单=${confirmForm}；权限提示=${warn}；可直接确认=${(await pd1.locator('button:has-text("确认建议")').count())}`,
    confirmForm === 0 && warn ? "正常" : "缺陷", nD2);
  await ctxD.close();

  // ================== cs ==================
  const ctxC = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "zh-CN" });
  ctxC.setDefaultTimeout(60000);
  const pc = await ctxC.newPage();
  attachLogs(pc);
  await pc.goto(`${BASE}/login?demo=cs`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 400);
  await pc.getByRole("button", { name: "登录" }).click();
  await pc.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 120000 });
  await pc.goto(`${BASE}/products/${PID}?tab=overview`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1500);
  const cText = await pc.locator("body").innerText();
  const cDel = await pc.locator('a[href$="/delete"]:has-text("删除商品")').count();
  const nC1 = await shot(pc, "p02-rbac-cs-product-overview");
  rec("P02·RBAC", "客服打开商品详情", "cs 登录并直连商品页",
    "只读 → 写操作按钮隐藏 + 只读提示",
    `删除商品=${cDel}；含只读提示=${cText.includes("只读")}；含保存商品=${cText.includes("保存商品")}`,
    cDel === 0 && cText.includes("只读") ? "正常" : "缺陷", nC1);
  await pc.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1400);
  const cMi = await pc.locator("body").innerText();
  const cGen = await pc.locator('button:has-text("生成主图")').count();
  rec("P02·RBAC", "客服主图 tab 写按钮", "cs 打开 main-images",
    "生成主图/编辑方案隐藏", `生成主图按钮=${cGen}；含「编辑方案」=${cMi.includes("编辑方案")}`,
    cGen === 0 && !cMi.includes("编辑方案") ? "正常" : "缺陷", "");
  await pc.goto(`${BASE}/products`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1200);
  const cList = await pc.locator("body").innerText();
  const cDelBtns = await pc.locator('a[href$="/delete"]').count();
  const nC2 = await shot(pc, "p02-rbac-cs-products-list");
  rec("P02·RBAC", "客服商品池列表", "cs 打开 /products",
    "行内删除按钮隐藏", `删除链接数=${cDelBtns}；列表含我的商品=${cList.includes(CREATED.productName)}`,
    cDelBtns === 0 ? "正常" : "缺陷", nC2);
  await ctxC.close();

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });