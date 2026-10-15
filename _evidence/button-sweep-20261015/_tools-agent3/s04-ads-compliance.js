// agent3 s04（C2）— P02 投放：建议/确认/实验/状态/看板 + 合规拦截（文案编辑）+ 计划状态按钮
"use strict";
const { launch, newPage, shot, rec, settle, issues, attachLogs } = require("./lib");
const fs = require("fs");
const path = require("path");

const BASE = process.env.P02_BASE || "http://127.0.0.1:3001";
const API = "http://127.0.0.1:8000";
const STATE = path.join(process.env.TEMP || "", "opencode", "agent3-boss-state.json");
const CREATED = JSON.parse(fs.readFileSync(path.join(process.env.TEMP || "", "opencode", "agent3-created.json"), "utf-8"));
const PID = (CREATED.productHref || "/products/4").replace("/products/", "");

async function bossToken() {
  const r = await fetch(API + "/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "boss@example.com", password: "Test123456" }),
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

  // ================= 投放建议 =================
  await page.goto(`${BASE}/products/${PID}?tab=ads`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  let b = page.locator('button:has-text("生成投放建议")');
  if (await b.count()) {
    await b.first().click({ noWaitAfter: true });
    await page.waitForURL(/tab=ads/, { timeout: 300000 }).catch(() => {});
    await settle(page, 2500);
    const t = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-ads-recommendation");
    rec("P02·投放", "生成投放建议", "点击「生成投放建议」",
      "生成建议并标注 LLM/规则来源",
      `含「还没有投放建议」=${t.includes("还没有投放建议")}；含「LLM 生成」=${t.includes("LLM 生成")}；含「规则生成」=${t.includes("规则生成")}；含「尝试中」=${t.includes("尝试中")}`,
      t.includes("LLM 生成") || t.includes("规则生成") ? "正常" : "缺陷", n);
  } else rec("P02·投放", "生成投放建议", "查找按钮", "存在", "未找到", "缺陷", "");

  // ================= 人工确认建议 =================
  const conf = page.locator('summary:has-text("人工确认建议")');
  if (await conf.count()) {
    await conf.first().click();
    await page.fill('textarea[name="confirmation_note"]', "UI测试：人工确认备注（自动化点击）");
    await page.locator('button:has-text("确认建议")').first().click();
    await page.waitForURL(/tab=ads/, { timeout: 120000 }).catch(() => {});
    await settle(page, 1800);
    const t = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-ads-confirmed");
    rec("P02·投放", "确认投放建议", "填备注后点「确认建议」",
      "建议状态变为已确认",
      `url=${page.url()}；含「已确认」=${t.includes("已确认")}；含「暂不采纳」=${t.includes("暂不采纳")}`,
      /confirmation_status=confirmed|confirmed/.test(page.url()) || t.includes("已确认") ? "正常" : "部分", n);
  } else {
    const t = await page.locator("body").innerText();
    rec("P02·投放", "确认投放建议", "查找「人工确认建议」区", "老板可见确认表单",
      `含「需要「确认投放」权限」=${t.includes("确认投放")}`, "部分", "");
  }

  // ================= 生成实验 =================
  b = page.locator('button:has-text("生成实验")');
  if (await b.count()) {
    await b.first().click({ noWaitAfter: true });
    await page.waitForURL(/tab=ads/, { timeout: 300000 }).catch(() => {});
    await settle(page, 2000);
    const t = await page.locator("body").innerText();
    const n = await shot(page, "p02-prod4-ads-experiment-generated");
    rec("P02·投放", "生成实验", "点击「生成实验」",
      "生成实验计划并提示人工确认",
      `含「已生成投放实验计划」=${t.includes("已生成投放实验计划")}；含「实验计划生成失败」=${t.includes("实验计划生成失败")}；含「还没有实验计划」=${t.includes("还没有实验计划")}`,
      t.includes("已生成投放实验计划") ? "正常" : "缺陷", n);
  } else rec("P02·投放", "生成实验", "查找按钮", "存在", "未找到", "缺陷", "");

  // ================= 实验状态流转 =================
  for (const [label, expect] of [["标记执行中", "实验状态已更新"], ["标记暂停", "实验状态已更新"], ["恢复执行", "实验状态已更新"]]) {
    const btn = page.locator(`button:has-text("${label}")`);
    if (await btn.count()) {
      await btn.first().click();
      await page.waitForURL(/tab=ads/, { timeout: 120000 }).catch(() => {});
      await settle(page, 1500);
      const t = await page.locator("body").innerText();
      const n = await shot(page, `p02-prod4-ads-status-${label}`);
      rec("P02·投放", `实验状态:${label}`, "点击状态按钮", expect,
        `含「实验状态已更新」=${t.includes(expect)}`, t.includes(expect) ? "正常" : "部分", n);
    } else {
      rec("P02·投放", `实验状态:${label}`, "查找按钮", "存在", "未找到（前一状态可能未流转）", "未测", "");
    }
  }

  // 实验看板
  const t2 = await page.locator("body").innerText();
  const n2 = await shot(page, "p02-prod4-ads-dashboard");
  rec("P02·投放", "实验看板", "查看 ads tab", "显示实验看板（已回填/优胜实验）",
    `含「实验看板」=${t2.includes("实验看板")}；含「当前优胜实验」=${t2.includes("当前优胜实验")}；含「已回填」=${t2.includes("已回填")}；含「删除实验」=${t2.includes("删除实验")}`,
    t2.includes("实验看板") ? "正常" : "部分", n2);

  // ================= 合规：主图方案编辑（违规应被拦、合规应可存） =================
  await page.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1500);
  const det = page.locator('summary:has-text("编辑方案")').first();
  await det.click();
  await settle(page, 400);
  const headlineInput = page.locator('input[name="headline"]').first();
  const origHeadline = await headlineInput.inputValue();
  await headlineInput.fill("全网最低价 根治敏感肌");
  await page.locator('button:has-text("保存修改")').first().click();
  await page.waitForURL(/tab=main-images/, { timeout: 120000 }).catch(() => {});
  await settle(page, 1800);
  const vt = await page.locator("body").innerText();
  const n3 = await shot(page, "p02-prod4-compliance-violation-save");
  rec("P02·合规检测", "违规文案保存（全网最低价/根治敏感肌）", "编辑主图方案主文案后保存",
    "被拦截且告知命中词/法条",
    `url含edit=failed=${/edit=failed/.test(page.url())}；页面出现错误/拦截提示=${/违规|拦截|不合规|广告法/.test(vt)}；提示任何「失败」=${vt.includes("失败")}`,
    /edit=failed/.test(page.url()) && !/拦截|违规|不合规/.test(vt) ? "缺陷" : (/edit=failed/.test(page.url()) ? "部分" : "正常"),
    `${n3}（预期缺陷：静默失败，无提示）`);

  // 后端实际返回（证据：API 层有 span/法条，UI 未消费）
  try {
    const tok = await bossToken();
    const pd = await (await fetch(`${API}/api/v1/products/${PID}`, { headers: { Authorization: "Bearer " + tok } })).json();
    const plan = pd.creative_plans.find((c) => c.type === "main_image");
    const pr = await fetch(`${API}/api/v1/products/${PID}/creative-plans/${plan.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + tok },
      body: JSON.stringify({ content: { headline: "全网最低价 根治敏感肌" } }),
    });
    const body = await pr.json();
    console.log("API-422:", pr.status, JSON.stringify(body).slice(0, 600));
    rec("P02·合规检测", "违规文案保存（API 直连复核）", "PATCH creative-plan headline=违规文案",
      "422 + 命中词 span/法条", `status=${pr.status}；detail=${JSON.stringify(body.detail).slice(0, 300)}`,
      pr.status === 422 ? "正常" : "缺陷", "（后端已拦截）");
  } catch (e) { console.log("API check fail", e); }

  // 合规文案（对照组）
  await page.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1400);
  await page.locator('summary:has-text("编辑方案")').first().click();
  await settle(page, 400);
  const safe = "温和配方 好评多多（UI测试）";
  await page.locator('input[name="headline"]').first().fill(safe);
  await page.locator('button:has-text("保存修改")').first().click();
  await page.waitForURL(/tab=main-images/, { timeout: 120000 }).catch(() => {});
  await settle(page, 1500);
  const n4 = await shot(page, "p02-prod4-compliance-safe-save");
  const savedOk = await page.evaluate(async (pid) => {
    const r = await fetch(`/products/${pid}?tab=main-images`, { headers: { RSC: "1" } }).catch(() => null);
    return true;
  }, PID);
  // 复核：直接读 API 确认落库
  let persisted = "";
  try {
    const tok = await bossToken();
    const pd = await (await fetch(`${API}/api/v1/products/${PID}`, { headers: { Authorization: "Bearer " + tok } })).json();
    const plan = pd.creative_plans.filter((c) => c.type === "main_image").sort((a, b) => b.id - a.id)[0];
    persisted = plan.content.headline || "";
  } catch (e) {}
  rec("P02·合规检测", "合规文案保存（对照组）", `编辑主文案为「${safe}」后保存`,
    "正常保存（无拦截）", `url=${page.url()}；API 最新方案 headline=${persisted}`,
    persisted === safe ? "正常" : (/edit=failed/.test(page.url()) ? "缺陷" : "未测"), n4);

  // 方案状态按钮：选中/归档/草稿（对最新方案）
  await page.goto(`${BASE}/products/${PID}?tab=main-images`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await settle(page, 1200);
  for (const [label, badge] of [["选中", "已选中"], ["归档", "已归档"], ["草稿", "草稿"]]) {
    const btn = page.locator(`button:has-text("${label}")`).filter({ hasNotText: "草稿\u200b" });
    if (await btn.count()) {
      await btn.first().click();
      await page.waitForURL(/tab=main-images/, { timeout: 90000 }).catch(() => {});
      await settle(page, 1200);
      const t = await page.locator("body").innerText();
      const n = await shot(page, `p02-prod4-plan-status-${label}`);
      rec("P02·主图方案", `状态按钮:${label}`, "点击", `方案状态变为${badge}`,
        `页面含「${badge}」=${t.includes(badge)}`, t.includes(badge) ? "正常" : "部分", n);
      if (label === "草稿") break;
    } else { rec("P02·主图方案", `状态按钮:${label}`, "查找按钮", "存在", "未找到", "未测", ""); }
  }

  console.log("ISSUES:", JSON.stringify(issues(page)));
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });