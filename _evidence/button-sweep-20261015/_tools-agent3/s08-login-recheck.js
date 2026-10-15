// agent3 s08 — 并发改动影响复核：P02 登录页快捷卡片(@example.com) vs 手动真实账号；公网手动登录全链路
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const PUB = "http://39.96.200.45:8090/p02";

(async () => {
  const browser = await launch();

  // ---------- 本地：快捷卡片现状 ----------
  {
    const { ctx, page } = await newPage(browser);
    await page.goto(BASE + "/login", { waitUntil: "domcontentloaded", timeout: 90000 });
    await settle(page, 1000);
    const chipLink = page.locator("a", { hasText: "example.com" }).first();
    const chipFound = await chipLink.count();
    let chipEmail = "", chipPw = "";
    if (chipFound) {
      await chipLink.click({ noWaitAfter: true });
      await settle(page, 1000);
      chipEmail = await page.locator("input[name=email]").inputValue();
      chipPw = await page.locator("input[name=password]").inputValue();
      await page.getByRole("button", { name: "登录" }).click({ noWaitAfter: true });
      await page.waitForTimeout(6000);
    }
    const t = await page.locator("body").innerText();
    const n = await shot(page, "local-login-chip-example-com");
    rec("P02·登录页", "快捷卡片现状(本地 11:07)", "点「老板」卡片→提交",
      "该卡片应能登录成功",
      `卡片邮箱=${chipEmail}；密码长度=${chipPw.length}；url=${page.url()}；含「邮箱或密码不正确」=${t.includes("邮箱或密码不正确")}`,
      t.includes("邮箱或密码不正确") ? "缺陷" : "正常", `${n}（11:05 起快捷卡片被并发改动为 @example.com，种子账号实为 @legacy.example.com）`);

    // 手动真实账号
    await page.goto(BASE + "/login", { waitUntil: "domcontentloaded", timeout: 90000 });
    await settle(page, 800);
    await page.fill("input[name=email]", "boss@legacy.example.com");
    await page.fill("input[name=password]", "Test123456");
    await page.getByRole("button", { name: "登录" }).click({ noWaitAfter: true });
    await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 90000 }).catch(() => {});
    const ok = !page.url().includes("/login");
    rec("P02·登录页", "手动真实账号登录(本地)", "手输 boss@legacy.example.com",
      "登录成功", `url=${page.url()}`, ok ? "正常" : "缺陷", "");
    await ctx.close();
  }

  // ---------- 公网：手动真实账号登录 ----------
  {
    const { ctx, page } = await newPage(browser);
    const reqs = [];
    page.on("response", (r) => { if (r.status() >= 400) reqs.push(`${r.status()} ${r.request().resourceType()} ${r.request().url()}`); });
    await page.goto(PUB + "/login", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
    await settle(page, 2500);
    await page.fill("input[name=email]", "boss@legacy.example.com");
    await page.fill("input[name=password]", "Test123456");
    await page.getByRole("button", { name: "登录" }).click({ noWaitAfter: true });
    await page.waitForTimeout(8000);
    const url = page.url();
    const t = await page.locator("body").innerText();
    const n = await shot(page, "pub-p02-login-manual");
    rec("公网·P02", "手动真实账号登录", "公网手输 boss@legacy.example.com/Test123456",
      "进入工作台（公网全链路可用）",
      `url=${url}；含「工作台」=${t.includes("工作台")}；含「邮箱或密码不正确」=${t.includes("邮箱或密码不正确")}；4xx=${JSON.stringify(reqs.slice(0, 6))}`,
      !url.includes("/login") || t.includes("工作台") ? "正常" : "缺陷", n);
    await ctx.close();
  }

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });