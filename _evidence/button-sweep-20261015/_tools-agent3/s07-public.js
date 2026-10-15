// agent3 s07 — 公网入口实测：P02(/p02/) 与 P03(/p03/) 能否在浏览器里真正跑起来
// 注意：同一 browser 内先做完 P02 公网，再开 P03 公网（cp_mod cookie 单值会串台）
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");

const P02PUB = "http://39.96.200.45:8090/p02/";
const P03PUB = "http://39.96.200.45:8090/p03/";

(async () => {
  const browser = await launch();

  // ---------- P02 公网 ----------
  {
    const { ctx, page } = await newPage(browser);
    const reqs = [];
    page.on("response", (r) => { if (r.status() >= 400) reqs.push(`${r.status()} ${r.request().resourceType()} ${r.url()}`); });
    await page.goto(P02PUB + "login", { waitUntil: "domcontentloaded", timeout: 60000 }).catch((e) => console.log("goto err", String(e).slice(0, 120)));
    await settle(page, 3500);
    const t1 = await page.locator("body").innerText().catch(() => "");
    const styled = await page.evaluate(() => {
      const btn = document.querySelector("button[type=submit]");
      if (!btn) return "no-button";
      const cs = getComputedStyle(btn);
      return `bg=${cs.backgroundColor} radius=${cs.borderRadius}`;
    });
    const n = await shot(page, "pub-p02-login");
    rec("公网·P02", "打开 /p02/login", "浏览器访问公网入口",
      "登录页正常样式 + 表单可提交",
      `含「演示账号」=${t1.includes("演示账号")}；按钮样式=${styled}；4xx/失败请求=${JSON.stringify(reqs.slice(0, 8))}`,
      t1.includes("演示账号") && reqs.length === 0 ? "正常" : "缺陷", n);

    // 尝试点老板快捷并登录
    const chip = page.locator("a", { hasText: "boss@legacy.example.com" }).first();
    if (await chip.count()) {
      await chip.click({ noWaitAfter: true }).catch(() => {});
      await settle(page, 1500);
      await page.getByRole("button", { name: "登录" }).click({ noWaitAfter: true }).catch(() => {});
      await page.waitForTimeout(6000);
      const url = page.url();
      const t2 = await page.locator("body").innerText().catch(() => "");
      const n2 = await shot(page, "pub-p02-after-login-click");
      rec("公网·P02", "提交登录(老板)", "点快捷填充→点「登录」",
        "登录成功进入工作台",
        `url=${url}；含「工作台」=${t2.includes("工作台")}；含「无法连接后端」=${t2.includes("无法连接后端")}；404请求=${JSON.stringify(reqs.slice(0, 6))}`,
        /\/p02\/?$/.test(url) || t2.includes("工作台") ? "正常" : "缺陷", n2);
    } else {
      rec("公网·P02", "提交登录(老板)", "点快捷填充→点「登录」", "登录页有快捷卡片", "未找到快捷卡片（页面未渲染 JS？）", "未测", "");
    }
    await ctx.close();
  }

  // ---------- P03 公网 ----------
  {
    const { ctx, page } = await newPage(browser);
    const reqs = [];
    page.on("response", (r) => { if (r.status() >= 400) reqs.push(`${r.status()} ${r.request().resourceType()} ${r.url()}`); });
    const fails = [];
    page.on("requestfailed", (r) => fails.push(`${r.url()} :: ${(r.failure() || {}).errorText}`));
    await page.goto(P03PUB, { waitUntil: "domcontentloaded", timeout: 60000 }).catch((e) => console.log("goto err", String(e).slice(0, 120)));
    await settle(page, 4000);
    const mounted = await page.evaluate(() => {
      const app = document.querySelector("#app");
      return app ? app.children.length : -1;
    });
    const t = await page.locator("body").innerText().catch(() => "");
    const n = await shot(page, "pub-p03-welcome");
    rec("公网·P03", "打开 /p03/", "浏览器访问公网入口",
      "Vue 应用挂载 + 欢迎屏",
      `#app 子节点=${mounted}；含「欢迎使用问数助手」=${t.includes("欢迎使用问数助手")}；4xx=${JSON.stringify(reqs.slice(0, 8))}；failed=${JSON.stringify(fails.slice(0, 5))}`,
      mounted > 0 && t.includes("欢迎使用问数助手") ? "正常" : "缺陷", n);
    await ctx.close();
  }

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });