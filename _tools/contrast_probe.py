#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""页面对比度 / 水合探针（无头 Edge + CDP）。

`.qoder/rules/02-技术规范.md` 定了硬门禁「任何文字色在其底色上对比度须 ≥ 4.5:1」，
而这类问题在源码里看不出来 —— 只有把 CSS 层叠算完、拿到 computed color 才能发现
（实例：ui-kit 令牌表里未分层的 `a{}` 压掉 Tailwind 的 `.text-white`，
链接型按钮变成蓝底蓝字，见 `_evidence/INDEX.md` D14）。

顺带查同一次事故的另一半：Next 16 dev server 会把 `/_next/*` 的 JS chunk
按 Origin 判成跨站并返回 403 —— 页面样式正常但 React 从不水合，
ECharts 一张画布都不画。所以这里同时报告 4xx 脚本、页面异常与 canvas 数。

用法：
    python _tools/contrast_probe.py <url> [--out shot.png] [--wait 5]
                                    [--login-form p02] [--ratio 4.5]

`--login-form p02` 会先向 P02 的 `/login/submit` 发一次真实表单登录（演示口令
与 `bootstrap_demo_users.py` 一致），再跳到目标页 —— 旗舰模块的会话是 httpOnly
Cookie，注入不了，只能真登。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import CDP, find_edge, free_port, http_json  # noqa: E402

P02_BASE = "http://127.0.0.1:3001"
P02_LOGIN = (
    "fetch('%s/login/submit',{method:'POST',"
    "headers:{'Content-Type':'application/x-www-form-urlencoded'},"
    "body:'email=boss@cloudpivot.com&password=Test123456',credentials:'include'})"
    ".then(r=>r.status)" % P02_BASE
)

# 逐元素把 computed color 与其有效底色做 WCAG 2.1 对比度；
# 底色要向上找到第一个非透明 background，否则白字叠白卡会被漏判。
PROBE = r"""
((MIN_RATIO) => {
  const parse = s => (String(s).match(/[\d.]+/g) || []).map(Number);
  const chan = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = rgb => 0.2126 * chan(rgb[0]) + 0.7152 * chan(rgb[1]) + 0.0722 * chan(rgb[2]);
  const alphaless = (css, el) => {
    const v = parse(css);
    if (v.length < 3) return null;
    if (css.indexOf('rgba') === 0 && (v[3] === undefined ? 1 : v[3]) === 0) return null;
    return v.slice(0, 3);
  };
  const bgOf = el => {
    let n = el, acc = null;
    while (n && n.nodeType === 1) {
      const c = getComputedStyle(n).backgroundColor;
      const rgb = alphaless(c, n);
      if (rgb) { acc = rgb; break; }
      n = n.parentElement;
    }
    return acc || alphaless(getComputedStyle(document.body).backgroundColor) || [255, 255, 255];
  };
  const fails = [];
  [...document.querySelectorAll('a,button,p,span,h1,h2,h3,h4,td,th,label,li,code,div')]
    .forEach(el => {
      if (el.children.length) return;                 // 只看叶子，避免重复计一次父级
      const text = (el.textContent || '').trim();
      if (!text) return;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || Number(cs.opacity) < 0.05 || cs.display === 'none') return;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) return;
      const fg = alphaless(cs.color, el);
      if (!fg) return;
      const bg = bgOf(el);
      const l1 = lum(fg), l2 = lum(bg);
      const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      if (ratio < MIN_RATIO) {
        fails.push({ ratio: Number(ratio.toFixed(2)), text: text.slice(0, 16),
                     tag: el.tagName.toLowerCase(), color: cs.color, bg: 'rgb(' + bg.join(',') + ')',
                     cls: String(el.className || '').slice(0, 46) });
      }
    });
  fails.sort((a, b) => a.ratio - b.ratio);
  return JSON.stringify({
    theme: document.documentElement.getAttribute('data-theme'),
    canvases: document.querySelectorAll('canvas').length,
    badScripts: performance.getEntriesByType('resource')
      .filter(r => /\.(js|css)$/.test(r.name) && r.responseStatus >= 400)
      .map(r => r.name.replace(/^https?:\/\/[^/]+/, '') + ' -> HTTP ' + r.responseStatus).slice(0, 8),
    errors: (window.__errs || []).slice(0, 5),
    lowContrast: fails.slice(0, 15),
    lowContrastCount: fails.length,
  });
})(__MIN_RATIO__)
"""


def run(url: str, out: str, login_form: str, wait: float, ratio: float) -> int:
    edge = find_edge()
    port = free_port()
    profile = tempfile.mkdtemp(prefix="edge-probe-")
    start = "%s/login" % P02_BASE if login_form == "p02" else url
    proc = subprocess.Popen(
        [edge, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
         "--no-default-browser-check", "--force-device-scale-factor=1", "--hide-scrollbars",
         "--mute-audio", "--allow-running-insecure-content", "--remote-allow-origins=*",
         "--user-data-dir=%s" % profile, "--remote-debugging-port=%d" % port,
         "--window-size=1600,1200"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp = None
    try:
        browser_ws = ""
        for _ in range(60):
            try:
                browser_ws = http_json("http://127.0.0.1:%d/json/version" % port).get(
                    "webSocketDebuggerUrl", "")
                if browser_ws:
                    break
            except Exception:
                time.sleep(0.5)
        if not browser_ws:
            print("! DevTools 未就绪")
            return 1
        br = CDP(browser_ws)
        target_id = br.send("Target.createTarget", {"url": start})["targetId"]
        br.close()
        tab_ws = ""
        for _ in range(60):
            try:
                for t in http_json("http://127.0.0.1:%d/json/list" % port):
                    if t.get("id") == target_id and t.get("webSocketDebuggerUrl"):
                        tab_ws = t["webSocketDebuggerUrl"]
                        break
            except Exception:
                pass
            if tab_ws:
                break
            time.sleep(0.5)
        if not tab_ws:
            print("! 找不到刚创建的 target")
            return 1

        cdp = CDP(tab_ws, timeout=90)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        # 错误钩子必须早于页面脚本，否则抓不到水合期异常
        cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": (
            "window.__errs=[];addEventListener('error',e=>__errs.push(String(e.message||e.error)"
            ".slice(0,240)));addEventListener('unhandledrejection',e=>__errs.push('rej:'+String(e.reason)"
            ".slice(0,240)));")})
        cdp.send("Emulation.setDeviceMetricsOverride",
                 {"width": 1600, "height": 1200, "deviceScaleFactor": 1, "mobile": False})

        if login_form == "p02":
            # about:blank 的 readyState 立刻就是 complete，要等真实页面提交后再发登录
            here = ""
            for _ in range(60):
                here = cdp.send("Runtime.evaluate", {"expression": "location.href",
                                                     "returnByValue": True}).get("result", {}).get("value", "")
                if str(here).startswith(P02_BASE):
                    break
                time.sleep(0.5)
            r = cdp.send("Runtime.evaluate", {"expression": P02_LOGIN, "awaitPromise": True,
                                              "returnByValue": True}, timeout=60)
            print("  登录 ->", (r.get("result") or {}).get("value") or r.get("exceptionDetails"))
            cdp.send("Page.navigate", {"url": url})
        cdp.wait_load(60)
        time.sleep(wait)          # 留给异步 fetch 与 ECharts 渲染

        res = cdp.send("Runtime.evaluate",
                       {"expression": PROBE.replace("__MIN_RATIO__", repr(float(ratio))),
                        "returnByValue": True}, timeout=40)
        raw = (res.get("result") or {}).get("value")
        if not raw:
            print("探针求值失败", res.get("exceptionDetails"))
            return 1
        report = json.loads(raw)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if out:
            data = base64.b64decode(cdp.send("Page.captureScreenshot",
                                             {"format": "png", "captureBeyondViewport": True})["data"])
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "wb") as f:
                f.write(data)
            print("截图 ->", out, "%d KB" % (len(data) // 1024))
        bad = report["badScripts"] or report["errors"] or report["lowContrastCount"]
        return 1 if bad else 0
    finally:
        if cdp:
            cdp.close()
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="", help="同时落一张全页截图")
    ap.add_argument("--login-form", default="", choices=["", "p02"],
                    help="先真实登录目标模块再访问（旗舰 P02 的会话是 httpOnly Cookie）")
    ap.add_argument("--wait", type=float, default=5.0)
    ap.add_argument("--ratio", type=float, default=4.5, help="对比度门禁，默认 4.5:1")
    a = ap.parse_args()
    print("探测 %s" % a.url)
    return run(a.url, a.out, a.login_form, a.wait, a.ratio)


if __name__ == "__main__":
    sys.exit(main())
