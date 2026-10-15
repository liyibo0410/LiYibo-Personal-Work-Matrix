# -*- coding: utf-8 -*-
"""S01 — PUBLIC P05 entry: /p05/ redirect target, login page asset/API resolution."""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from agent4_lib import *

TAG = "P05(公网)"

with Session() as s:
    page = s.new_page(TAG)

    # --- 1. entry URL /p05/
    resp = page.goto(P05_PUB, wait_until="domcontentloaded")
    settle(page, 1200)
    final = page.url
    title = page.title()
    body_head = page.inner_text("body")[:200].replace("\n", " | ")
    shot(page, "p05-public-entry-302-result")
    rec(TAG, "入口", "GET /p05/", "直接访问公网入口",
        "302 → 落到 /p05/login（前缀内）",
        f"最终 URL={final} | title={title} | 页面文本={body_head[:120]}",
        "缺陷" if "/login" in final and "p05" not in final else "正常",
        evidence="screenshot agent4-01")

    # --- 2. direct /p05/login (bypass redirect)
    page.goto(P05_PUB + "login", wait_until="domcontentloaded")
    settle(page, 1500)
    iss = s.issues(page)
    shot(page, "p05-public-login-page")
    assets_404 = [x for x in iss["http4xx"] if "/p05/" not in x]
    rec(TAG, "登录页", "加载 /p05/login 静态资源",
        "页面引用的 /assets/app.css、/assets/app.js 等绝对路径",
        "均前缀化 /p05/assets/* 加载成功",
        f"非前缀资源 4xx={assets_404[:6]}",
        "缺陷" if any("/assets/" in x for x in assets_404) else "正常",
        evidence="")

    # --- 3. one-click role login on public
    clicked = False
    try:
        btn = page.locator(".role-item").first
        btn.click(timeout=5000)
        clicked = True
        page.wait_for_timeout(2500)
    except Exception as e:  # noqa: BLE001
        rec(TAG, "登录页", "一键进入（legal）", "点击角色按钮",
            "调用 /api/auth/switch 后跳转 /", f"按钮点击失败：{e}", "未测", "")
    if clicked:
        err = ""
        try:
            err = page.locator("#loginErr").inner_text(timeout=2000)
        except Exception:
            pass
        shot(page, "p05-public-login-role-click")
        rec(TAG, "登录页", "一键进入（legal）", "点击角色按钮",
            "登录成功并进入大盘",
            f"最终URL={page.url} | loginErr=「{err}」",
            "缺陷" if "/login" in page.url else "正常",
            evidence="screenshot agent4-03")

    # --- 4. manual credential login (legal / Legal@2026)
    page.goto(P05_PUB + "login", wait_until="domcontentloaded")
    settle(page, 900)
    try:
        page.fill("#u", "legal")
        page.fill("#p", "Legal@2026")
        page.click("#loginBtn")
        page.wait_for_timeout(2500)
        err = ""
        try:
            err = page.locator("#loginErr").inner_text(timeout=2000)
        except Exception:
            pass
        shot(page, "p05-public-login-manual")
        rec(TAG, "登录页", "账号口令登录（legal）", "填写凭证并提交",
            "登录成功并进入大盘",
            f"最终URL={page.url} | loginErr=「{err}」",
            "缺陷" if "/login" in page.url else "正常", "")
    except Exception as e:  # noqa: BLE001
        rec(TAG, "登录页", "账号口令登录（legal）", "填写凭证并提交",
            "登录成功并进入大盘", f"异常：{e}", "缺陷", "")

    # --- 5. API prefix probe from page context
    probe = page.evaluate("""async () => {
      const out = {};
      for (const u of ['/api/health', '/p05/api/health']) {
        try { const r = await fetch(u); out[u] = r.status + ' ' + (await r.text()).slice(0, 80); }
        catch (e) { out[u] = 'ERR ' + e.message; }
      }
      return out;
    }""")
    rec(TAG, "登录页", "API 前缀探针（页面内 fetch）", "对比 /api vs /p05/api",
        "/api/* 应由 P05 应答",
        str(probe), "缺陷", "")

print("S01 DONE")