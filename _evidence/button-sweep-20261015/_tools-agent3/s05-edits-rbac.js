// agent3 s05 — P02 编辑路径（商品/视频脚本/诊断）+ 广告确认态复核 + RBAC(design/cs) 按钮级
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
async function getProduct(tok) {
  return (await fetch(`${API}/api/v1/products/${PID}`, { headers: { Authorization: "Bearer " + tok } })).json();
}

(async () => {
  const browser = await launch();
  const bossTok = await tokenFor("boss@legacy.example.com");

  // ================== 老板上下文：编辑 ==================
  const ctx = await browser.newContext({
    viewport: { width: 1500, height: 950 }, locale: "zh-CN", timezoneId: "Asia/Shanghai",
    storageState: fs.existsSync(STATE) ? STATE : undefined,
  });
  ctx.setDefaultTimeout(60000);
  const page = await ctx.newPage();
  attachLogs(page);

  // ---- 1. 保存商品（商品池「编辑」） ----
  await page.goto(`${BASE}/products/${PID}?tab=overview`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  await page.locator('form[action="/products/' + PID + '/update"] input[name="category"]').fill("测试类目-改");
  await page.locator('form[action="/products/' + PID + '/update"] input[name="target_audience"]').fill("UI测试人群");
  await page.locator('button:has-text("保存商品")').first().click({ noWaitAfter: true });
  await page.waitForTimeout(4000);
  let pd = await getProduct(bossTok);
  const n1 = await shot(page, "p02-prod4-product-edit-saved");
  rec("P02·商品详情", "保存商品（编辑）", "改类目/目标人群后点「保存商品」",
    "保存生效并回到商品页", `url=${page.url()}；API category=${pd.category}；target_audience=${pd.target_audience}`,
    pd.category === "测试类目-改" ? "正常" : "缺陷", n1);

  // ---- 2. 视频脚本编辑保存 ----
  await page.goto(`${BASE}/products/${PID}?tab=video`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const vsummary = page.locator('summary:has-text("编辑脚本")');
  const vcount = await vsummary.count();
  if (vcount) {
    await vsummary.first().click();
    await settle(page, 400);
    const before = (await getProduct(bossTok)).creative_plans.filter((c) => c.type === "video_script").sort((a, b) => b.id - a.id)[0];
    await page.locator('input[name="title"]').first().fill("UI测试脚本标题-改");
    await page.locator('button:has-text("保存修改")').first().click({ noWaitAfter: true });
    await page.waitForTimeout(4000);
    const after = (await getProduct(bossTok)).creative_plans.filter((c) => c.type === "video_script").sort((a, b) => b.id - a.id)[0];
    const n2 = await shot(page, "p02-prod4-video-edit-save");
    rec("P02·商品详情", "视频脚本编辑保存", "改脚本标题后保存",
      "保存生效", `url=${page.url()}；API 标题 before=${before.title} after=${after.title}`,
      after.title === "UI测试脚本标题-改" ? "正常" : "缺陷", n2 + "（疑似同 main-image 鉴权缺失根因）");
  } else {
    rec("P02·商品详情", "视频脚本编辑保存", "查找「编辑脚本」", "存在", "未找到", "未测", "");
  }

  // ---- 3. 诊断编辑保存 ----
  await page.goto(`${BASE}/products/${PID}?tab=diagnosis`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const dsummary = page.locator('summary:has-text("编辑诊断")');
  if (await dsummary.count()) {
    await dsummary.first().click();
    await settle(page, 400);
    const inputs = page.locator('form[action*="/diagnoses/"] input[type="text"], form[action*="/diagnoses/"] textarea');
    const cnt = await inputs.count();
    let target = null;
    for (let i = 0; i < cnt; i++) {
      const v = await inputs.nth(i).inputValue().catch(() => "");
      if (v && v.length > 3) { target = inputs.nth(i); break; }
    }
    if (target) {
      await target.fill("UI测试诊断编辑：定位建议改为测试用文本");
      await page.locator('button:has-text("保存修改")').first().click({ noWaitAfter: true });
      await page.waitForTimeout(4000);
      const n3 = await shot(page, "p02-prod4-diagnosis-edit-save");
      const dtext = await page.locator("body").innerText();
      rec("P02·商品详情", "诊断编辑保存", "改诊断文本后保存",
        "保存生效或给出失败提示", `url=${page.url()}；页面含「UI测试诊断编辑」=${dtext.includes("UI测试诊断编辑")}`,
        dtext.includes("UI测试诊断编辑") ? "正常" : (/failed|失败/.test(page.url() + dtext) ? "缺陷" : "部分"), n3);
    } else {
      rec("P02·商品详情", "诊断编辑保存", "查找可编辑字段", "存在", "未找到", "未测", "");
    }
  } else {
    rec("P02·商品详情", "诊断编辑保存", "查找「编辑诊断」", "存在", "未找到", "未测", "");
  }

  // ---- 4. 投放建议「已确认」态复核（rec#7 已确认） ----
  await page.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 2000);
  const ads = await page.locator("body").innerText();
  const badge = ads.match(/(待确认|已确认|暂不采纳|已驳回|规则生成|LLM 生成)/g);
  const n4 = await shot(page, "p02-prod4-ads-confirmed-recheck");
  rec("P02·投放", "已确认建议态复核", "重开 ads tab 读徽标",
    "确认后的建议显示已确认", `命中徽标=${JSON.stringify([...new Set(badge || [])])}`,
    (badge || []).includes("已确认") ? "正常" : "部分", n4);

  await ctx.close();

  // ================== design 角色 ==================
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
  await settle(pd1, 1800);
  const dAds = await pd1.locator("body").innerText();
  const confirmForm = await pd1.locator('summary:has-text("人工确认建议")').count();
  const warn = dAds.includes("需要「确认投放」权限");
  const nD2 = await shot(pd1, "p02-rbac-design-ads-confirm");
  rec("P02·RBAC", "美工广告确认权限", "design 打开 ads tab",
    "无 can_confirm_ad_actions → 确认表单隐藏、显示权限提示",
    `确认表单=${confirmForm}；权限提示=${warn}`, confirmForm === 0 && warn ? "正常" : "缺陷", nD2);
  await ctxD.close();

  // ================== cs 角色 ==================
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
  await settle(pc, 1200);
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