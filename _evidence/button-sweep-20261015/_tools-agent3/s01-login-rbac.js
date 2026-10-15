// agent3 s01 — P02 本地登录 / 四角色 / 错误口令 / 登出 / RBAC 直连受限页
// 入口：http://127.0.0.1:3001 （本地；公网隧道 10:26 实测 502，先本地）
"use strict";
const { launch, newPage, shot, rec, issues, settle } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const PW = "Test123456";
const ACCOUNTS = {
  boss: "boss@example.com",
  ops: "ops@example.com",
  design: "design@example.com",
  cs: "cs@example.com",
};

async function navItems(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("aside nav a")).map((a) => a.textContent.trim())
  );
}
async function headerText(page) {
  return (await page.locator("header").first().innerText().catch(() => "")).replace(/\s+/g, " ").trim();
}

(async () => {
  const browser = await launch();
  const { ctx, page } = await newPage(browser);
  let n;

  // ---------- 1. 登录页渲染 ----------
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded", timeout: 90000 });
  await settle(page, 1200);
  const loginText = await page.locator("body").innerText();
  n = await shot(page, "p02-login-page");
  rec("P02·登录页", "页面渲染", "打开 /login", "登录表单+四账号快捷填充可见",
    `title=${await page.title()}；含「演示账号」=${loginText.includes("演示账号")}；含密码 ${PW}=${loginText.includes(PW)}；按钮=${await page.getByRole("button", { name: "登录" }).count()}`, "正常", n);

  // ---------- 2. 点「老板」快捷填充 ----------
  await page.locator("a", { hasText: "boss@example.com" }).first().click();
  await settle(page, 800);
  const emailVal = await page.locator("input[name=email]").inputValue();
  const pwVal = await page.locator("input[name=password]").inputValue();
  n = await shot(page, "p02-login-chip-boss-filled");
  rec("P02·登录页", "演示账号快捷填充(老板)", "点击 boss@example.com 卡片",
    "邮箱与密码自动填入", `email=${emailVal} password长度=${pwVal.length}`, emailVal === ACCOUNTS.boss && pwVal.length > 0 ? "正常" : "缺陷", n);

  // ---------- 3. 错误口令 ----------
  await page.fill("input[name=email]", ACCOUNTS.boss);
  await page.fill("input[name=password]", "wrong-password-123");
  await page.getByRole("button", { name: "登录" }).click();
  await page.waitForURL(/\/login\?error=/, { timeout: 60000 }).catch(() => {});
  await settle(page, 600);
  const errText = (await page.locator("body").innerText()).includes("邮箱或密码不正确");
  n = await shot(page, "p02-login-wrong-password");
  rec("P02·登录页", "错误口令提交", "输入错误密码后点「登录」",
    "回到登录页并提示「邮箱或密码不正确」", `url=${page.url()}；出现错误提示=${errText}`, errText ? "正常" : "缺陷", n);

  // ---------- 4. 老板正确登录 ----------
  await page.locator("a", { hasText: "boss@example.com" }).first().click();
  await settle(page, 500);
  await page.getByRole("button", { name: "登录" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 120000 });
  await settle(page, 1500);
  let items = await navItems(page);
  n = await shot(page, "p02-home-boss");
  rec("P02·登录页", "老板登录", "boss@example.com / Test123456",
    "进入工作台且 7 个导航可见", `url=${page.url()}；导航=${JSON.stringify(items)}；顶栏=${await headerText(page)}`,
    page.url().includes("127.0.0.1:3001/") && items.length === 7 ? "正常" : "缺陷", n);

  // ---------- 5. 登出 ----------
  await page.getByRole("button", { name: "退出" }).click();
  await page.waitForURL(/\/login/, { timeout: 60000 });
  await settle(page, 600);
  n = await shot(page, "p02-after-logout");
  rec("P02·顶栏", "退出登录", "点击「退出」", "回到 /login", `url=${page.url()}`, page.url().includes("/login") ? "正常" : "缺陷", n);

  // 登出后访问 / 应被送回登录页
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 90000 });
  await settle(page, 600);
  rec("P02·工作台", "未登录访问受保护页", "登出后打开 /",
    "重定向到 /login", `url=${page.url()}`, page.url().includes("/login") ? "正常" : "缺陷", "");

  // ---------- 6. 四个角色登录 + RBAC ----------
  const roleExpect = {
    boss: { nav: 7, dashAllowed: true },
    ops: { nav: 7, dashAllowed: false },
    design: { nav: 6, dashAllowed: false },
    cs: { nav: 5, dashAllowed: false },
  };
  for (const key of ["ops", "design", "cs", "boss"]) {
    await page.goto(BASE + `/login?demo=${key}`, { waitUntil: "domcontentloaded", timeout: 90000 });
    await settle(page, 500);
    await page.getByRole("button", { name: "登录" }).click();
    await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 120000 });
    await settle(page, 1200);
    items = await navItems(page);
    const exp = roleExpect[key];
    n = await shot(page, `p02-home-role-${key}`);
    rec(`P02·RBAC`, `角色登录(${key})`, `登录 ${ACCOUNTS[key]}`,
      `导航 ${exp.nav} 项`, `导航=${JSON.stringify(items)}；顶栏=${await headerText(page)}`,
      items.length === exp.nav ? "正常" : "缺陷", n);

    // 直连 /dashboard
    await page.goto(BASE + "/dashboard", { waitUntil: "domcontentloaded", timeout: 90000 });
    await settle(page, 900);
    const url = page.url();
    const body = await page.locator("body").innerText();
    const hit = exp.dashAllowed ? url.includes("/dashboard") : url.includes("forbidden=dashboard");
    n = await shot(page, `p02-rbac-dashboard-${key}`);
    rec("P02·RBAC", `直连 /dashboard(${key})`, "goto /dashboard",
      exp.dashAllowed ? "老板可见经营总览" : "非老板被重定向回工作台",
      `url=${url}；页面含「经营总览」=${body.includes("经营总览")}；含「仅老板可见」=${body.includes("仅老板可见")}；含 forbidden 提示文案=${body.includes("无权") || body.includes("没有权限")}`,
      hit ? (exp.dashAllowed === body.includes("经营总览") ? "正常" : "部分") : "缺陷", n);

    // cs/design 直连 /settings
    if (key === "cs") {
      await page.goto(BASE + "/settings", { waitUntil: "domcontentloaded", timeout: 90000 });
      await settle(page, 900);
      const sbody = await page.locator("body").innerText();
      n = await shot(page, "p02-rbac-settings-cs");
      rec("P02·RBAC", "直连 /settings(客服)", "goto /settings",
        "客服在导航中隐藏该项", `url=${page.url()}；页面渲染=${sbody.length > 50}；含「模型配置」=${sbody.includes("模型配置")}`,
        page.url().includes("/settings") ? "缺陷" : "正常", n);
    }
    if (key === "design") {
      await page.goto(BASE + "/imports", { waitUntil: "domcontentloaded", timeout: 90000 });
      await settle(page, 900);
      const ibody = await page.locator("body").innerText();
      n = await shot(page, "p02-rbac-imports-designer");
      rec("P02·RBAC", "直连 /imports(美工)", "goto /imports",
        "美工导航中含该项，应可访问", `url=${page.url()}；含「数据导入」=${ibody.includes("数据导入")}`,
        page.url().includes("/imports") ? "正常" : "缺陷", n);
    }
  }

  // 保存 boss 登录态给后续脚本复用
  const statePath = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
  fs.writeFileSync(statePath, JSON.stringify(await ctx.storageState()));
  console.log("ISSUES(boss-page):", JSON.stringify(issues(page)));
  console.log("STATE_SAVED:", statePath);
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });