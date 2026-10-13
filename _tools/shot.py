#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""无头 Edge + CDP 截图取证工具。

验收门禁要的是「页面真的渲染出来了」的证据 —— 需要 JS 跑完之后的位图，
不是 HTML 源码，所以不能用 curl 代替。

用法：
    python _tools/shot.py <url> <输出.png> [--wait 3] [--w 1600 --h 1000]
                                   [--module p07] [--shell-login]

`--module` 会把截图直接落到 _evidence/<模块>/ 下，省一步手工搬文件。

踩过的坑（不要再改回去）：
  · 挂 Edge 启动自带的那个 tab 不可靠 —— 加载期间它是 type=other，
    启动收尾时还可能被销毁，表现为 WinError 10053 连接中止。
    所以这里显式 Target.createTarget，再用返回的 targetId 去 /json/list
    找它的页面级 WebSocket。
  · `--disable-features=Translate` 会让无头 Edge 不产出 page target。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

import websocket  # websocket-client

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_edge() -> str:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到 msedge.exe")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_json(url: str, timeout: float = 3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


class CDP:
    """最小 CDP 客户端（页面级 endpoint，不用 sessionId）。"""

    def __init__(self, ws_url: str, timeout: float = 40):
        self.ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0

    def send(self, method: str, params=None, timeout: float = 60):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        self.ws.settimeout(timeout)
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})

    def wait_load(self, timeout: float = 30) -> str:
        """轮询 readyState，比固定 sleep 更稳。"""
        end = time.time() + timeout
        state = ""
        while time.time() < end:
            try:
                r = self.send("Runtime.evaluate", {
                    "expression": "document.readyState", "returnByValue": True}, timeout=10)
                state = (r.get("result") or {}).get("value") or ""
            except Exception:
                state = ""
            if state == "complete":
                return state
            time.sleep(0.4)
        return state

    def drain(self, seconds: float):
        self.ws.settimeout(seconds)
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.ws.recv()
            except websocket.WebSocketTimeoutException:
                break
            except Exception:
                break

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def capture(url: str, out: str, wait: float, w: int, h: int, exec_js: str = "",
            probe_js: str = "") -> bool:
    edge = find_edge()
    port = free_port()
    profile = tempfile.mkdtemp(prefix="edge-shot-")
    args = [
        edge, "--headless=new", "--disable-gpu", "--no-first-run",
        "--disable-extensions", "--no-default-browser-check",
        "--force-device-scale-factor=1", "--hide-scrollbars", "--mute-audio",
        "--allow-running-insecure-content", "--remote-allow-origins=*",
        "--user-data-dir=%s" % profile,
        "--remote-debugging-port=%d" % port,
        "--window-size=%d,%d" % (w, h),
    ]
    # 注入登录态必须先落在目标 origin 的**真实页面**上：用 /api/health 这类 JSON 响应会被
    # Edge 的 JSON 查看器（扩展页）接管，sessionStorage 写到扩展的 origin 上，等于没写。
    start_url = url

    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                pass
            time.sleep(0.5)
        if not browser_ws:
            print("  ! DevTools 未就绪")
            return False

        br = CDP(browser_ws)
        target_id = br.send("Target.createTarget", {"url": start_url})["targetId"]
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
            print("  ! 找不到刚创建的 target")
            return False

        cdp = CDP(tab_ws)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("Emulation.setDeviceMetricsOverride",
                 {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
        if exec_js:
            cdp.wait_load(20)
            res = cdp.send("Runtime.evaluate", {"expression": exec_js, "returnByValue": True})
            if probe_js:
                err = res.get("exceptionDetails")
                print("  inject ->", "EXC %s" % json.dumps(err, ensure_ascii=False)[:300]
                      if err else "ok (%s)" % (res.get("result") or {}).get("type"))
            # 不能用 Page.navigate 跳回同一个 URL：同文档（尤其带相同 #hash）会被当成空操作，
            # 页面脚本不会重跑，登录态就像没写一样。
            cdp.send("Page.reload", {"ignoreCache": True})
        cdp.wait_load(30)
        if probe_js:
            try:
                r = cdp.send("Runtime.evaluate",
                             {"expression": probe_js, "returnByValue": True, "awaitPromise": True})
                print("  eval ->", json.dumps((r.get("result") or {}).get("value"),
                                              ensure_ascii=False)[:600])
            except Exception as exc:
                print("  eval !", exc)
        time.sleep(wait)          # 留给异步 fetch / ECharts 渲染
        cdp.drain(0.2)
        data = base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png"})["data"])
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
        print("  -> %s (%d KB)" % (out, len(data) // 1024))
        return True
    except Exception as exc:
        print("  ! %s: %s" % (type(exc).__name__, exc))
        return False
    finally:
        if cdp:
            cdp.close()
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def shell_login_js(theme: str = "") -> str:
    """取一个真实外壳令牌，返回写 sessionStorage 的 JS。"""
    body = json.dumps({"username": "owner",
                       "password": os.environ.get("SHELL_PW", "owner123")}).encode()
    req = urllib.request.Request("http://127.0.0.1:8800/api/auth/login", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        j = json.load(r)
    # 中文用户名走 percent-encoding 再在页面里 decode；实参必须是带引号的字符串字面量，
    # 直接拼 %7B... 会变成裸标识符，整段 JS 抛 SyntaxError 导致一条都没写进去。
    encoded = urllib.parse.quote(json.dumps(j["user"], ensure_ascii=False), safe="")
    js = ("sessionStorage.setItem('cp_token', %s); "
          "sessionStorage.setItem('cp_user', decodeURIComponent(%s));"
          % (json.dumps(j["token"]), json.dumps(encoded)))
    if theme in ("light", "dark"):
        js += " localStorage.setItem('cp_theme', %s);" % json.dumps(theme)
    return js


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--wait", type=float, default=3.0)
    ap.add_argument("--w", type=int, default=1600)
    ap.add_argument("--h", type=int, default=1000)
    ap.add_argument("--exec", dest="exec_js", default="")
    ap.add_argument("--probe", dest="probe_js", default="",
                    help="截图前在页面里求值并打印结果，用于断言状态")
    ap.add_argument("--shell-login", action="store_true", help="注入真实外壳登录态")
    ap.add_argument("--theme", default="", choices=["", "light", "dark"], help="注入主题偏好")
    ap.add_argument("--module", default="", help="落到 _evidence/<module>/ 下")
    args = ap.parse_args()

    out = args.out
    if args.module:
        out = os.path.join(REPO, "_evidence", args.module, os.path.basename(args.out))
    js = shell_login_js(args.theme) if args.shell_login else args.exec_js
    if args.theme and not args.shell_login:
        js = "localStorage.setItem('cp_theme', %s); %s" % (json.dumps(args.theme), js)
    print("截图 %s" % args.url)
    return 0 if capture(args.url, out, args.wait, args.w, args.h, js, args.probe_js) else 1


if __name__ == "__main__":
    sys.exit(main())
