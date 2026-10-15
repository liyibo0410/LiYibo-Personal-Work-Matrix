// agent3 s06 — 清理：删掉自建「UI测试-可删-agent3」商品 与「UI测试-可删-店铺」店铺（只删自己建的）
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const API = "http://127.0.0.1:8000";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

async function bossTok() {
  const r = await fetch(API + "/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "boss@legacy.example.com", password: "Test123456" }),
  });
  return (await r.json()).access_token;
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
  page.on("dialog", async (d) => { console.log("DIALOG:", d.type(), d.message().slice(0, 100)); await d.accept(); });

  // ---- 1. 删除商品（两步确认页） ----
  await page.goto(`${BASE}/products/${PID}/delete`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  const n1 = await shot(page, "p02-cleanup-product-delete-confirm");
  await page.locator('button:has-text("确认删除商品")').first().click({ noWaitAfter: true });
  await page.waitForTimeout(4000);
  const after = await page.locator("body").innerText();
  const n2 = await shot(page, "p02-cleanup-product-deleted");
  rec("P02·清理", "删除自建商品", "确认删除「UI测试-可删-agent3」",
    "删除成功并回商品池提示",
    `url=${page.url()}；含「商品已删除」=${after.includes("商品已删除")}`, after.includes("商品已删除") ? "正常" : (page.url().includes("/login") ? "缺陷" : "部分"), n2);

  // ---- 2. 删除自建店铺（window.confirm） ----
  await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1800);
  const storeBtn = page.locator('button:has-text("删除店铺")').filter({ hasText: "删除店铺" });
  const cnt = await storeBtn.count();
  let clicked = false;
  for (let i = 0; i < cnt; i++) {
    const card = storeBtn.nth(i).locator("xpath=ancestor::*[contains(@class,'rounded')][1]");
    const txt = await page.locator('form[action*="/delete"]').nth(i).getAttribute("action");
    if (txt && txt.includes("/" + (CREATED.storeAction || "").replace(/[^0-9]/g, "") + "/")) {
      await storeBtn.nth(i).click({ noWaitAfter: true });
      clicked = true;
      break;
    }
  }
  if (!clicked) {
    // 兜底：按店铺名找卡片里的表单
    const form = page.locator(`form[action="${CREATED.storeAction}"]`);
    if (await form.count()) { await form.locator('button[type=submit]').first().click({ noWaitAfter: true }); clicked = true; }
  }
  await page.waitForTimeout(4000);
  const t2 = await page.locator("body").innerText();
  const n3 = await shot(page, "p02-cleanup-store-deleted");
  rec("P02·清理", "删除自建店铺", "点击「删除店铺」并确认弹窗",
    "删除成功并提示店铺已删除",
    `clicked=${clicked}；url=${page.url()}；含「店铺已删除」=${t2.includes("店铺已删除")}`,
    t2.includes("店铺已删除") ? "正常" : "部分", n3);

  // ---- 3. API 复核 ----
  const tok = await bossTok();
  const products = await (await fetch(`${API}/api/v1/products`, { headers: { Authorization: "Bearer " + tok } })).json();
  const stores = await (await fetch(`${API}/api/v1/stores`, { headers: { Authorization: "Bearer " + tok } })).json();
  const leftoverP = products.filter((p) => p.name.includes("UI测试"));
  const leftoverS = stores.filter((s) => s.name.includes("UI测试"));
  rec("P02·清理", "清理复核(API)", "查 products/stores",
    "无 UI测试 残留",
    `products=${products.length}(残留${leftoverP.length})；stores=${stores.length}(残留${leftoverS.length})`,
    leftoverP.length === 0 && leftoverS.length === 0 ? "正常" : "部分", "");

  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });