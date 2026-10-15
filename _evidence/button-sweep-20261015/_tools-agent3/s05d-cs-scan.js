// agent3 s05d — cs(只读) 逐 tab 枚举写按钮泄漏 + 实测点击「生成主图」
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

const WRITE_WORDS = ["生成", "保存", "创建", "添加", "删除", "导入", "同步", "启动", "标记", "选中", "归档", "取消", "重试", "确认"];

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
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "zh-CN" });
  ctx.setDefaultTimeout(60000);
  const pc = await ctx.newPage();
  attachLogs(pc);
  await loginAs(pc, "cs@legacy.example.com");

  const tabs = ["overview", "agent", "diagnosis", "main-images", "video", "assets", "links", "ads", "jobs", "review"];
  const leaks = {};
  for (const key of tabs) {
    await pc.goto(`${BASE}/products/${PID}?tab=${key}`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await settle(pc, 1100);
    const btns = await pc.evaluate((words) =>
      [...new Set(Array.from(document.querySelectorAll("button"))
        .map((b) => (b.innerText || "").trim())
        .filter((t) => t && words.some((w) => t.includes(w))))], WRITE_WORDS);
    leaks[key] = btns;
    if (btns.length) console.log(`cs 可见写按钮 @${key}:`, JSON.stringify(btns));
  }
  rec("P02·RBAC", "客服只读全 tab 写按钮扫描", "cs 逐 tab 枚举按钮",
    "写类按钮应全部隐藏（页面提示只读）",
    `泄漏清单=${JSON.stringify(leaks)}`,
    Object.values(leaks).flat().length === 0 ? "正常" : "缺陷", "");
  const n = await shot(pc, "p02-rbac-cs-main-images-buttons");

  // 实测：cs 点「生成主图」
  await pc.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(pc, 1200);
  const gen = pc.locator('button:has-text("生成主图")');
  if (await gen.count()) {
    await gen.first().click({ noWaitAfter: true });
    await pc.waitForTimeout(4000);
    const t = await pc.locator("body").innerText();
    const n2 = await shot(pc, "p02-rbac-cs-generate-click");
    rec("P02·RBAC", "客服点击「生成主图」", "cs 点击泄漏的写按钮",
      "被后端拒绝且前端如实提示无权限",
      `url=${pc.url()}；含「失败」提示=${t.includes("失败")}；含「权限」=${t.includes("权限")}；生成后方案数=` + `${(await pc.locator('summary:has-text("编辑方案")').count())}`,
      /mainImagePlans=failed/.test(pc.url()) && !t.includes("权限") ? "缺陷" : "正常", n2);
  } else rec("P02·RBAC", "客服点击「生成主图」", "查找按钮", "存在（泄漏）", "未找到", "未测", "");
  await ctx.close();
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });