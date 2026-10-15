# -*- coding: utf-8 -*-
"""agent4 sweep library — Playwright based, evidence to _evidence/button-sweep-20261015/.

Constraints honoured:
- No repo code/config/service is modified.
- Screenshots land in the evidence folder as agent4-<seq>-<desc>.png
- Records appended to rows.jsonl (one JSON per control tested).
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from playwright.sync_api import sync_playwright

WORKSPACE = Path(r"D:\software\PycharmProjects\作品矩阵")
EV = WORKSPACE / "_evidence" / "button-sweep-20261015"
STATE = Path(os.environ["TEMP"]) / "opencode" / "agent4-state.json"
ROWS = Path(os.environ["TEMP"]) / "opencode" / "agent4-rows.jsonl"
DL_DIR = Path(os.environ["TEMP"]) / "opencode" / "agent4-downloads"

P05_PUB = "http://39.96.200.45:8090/p05/"
P08_PUB = "http://39.96.200.45:8090/p08/"
P05_LOC = "http://127.0.0.1:8770"
P08_LOC = "http://127.0.0.1:8080"


def _seq_next():
    try:
        st = json.loads(STATE.read_text("utf-8"))
    except Exception:
        st = {"seq": 0}
    st["seq"] = int(st.get("seq", 0)) + 1
    STATE.write_text(json.dumps(st), "utf-8")
    return st["seq"]


def shot(page, desc, full=False):
    EV.mkdir(parents=True, exist_ok=True)
    n = _seq_next()
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in desc)[:60]
    fn = f"agent4-{n:02d}-{safe}.png"
    page.screenshot(path=str(EV / fn), full_page=full)
    return fn


def rec(page_tag, screen, control, action, expected, actual, verdict, evidence=""):
    row = {
        "t": datetime.now().strftime("%H:%M:%S"),
        "page": page_tag,
        "screen": screen,
        "control": control,
        "action": action,
        "expected": expected,
        "actual": actual,
        "verdict": verdict,
        "evidence": evidence,
    }
    with ROWS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[{verdict.upper()}] {page_tag} | {control} | {str(actual)[:180]}")


class Session:
    """One browser + one context; page listeners collect console/network issues."""

    def __init__(self, module="p05", viewport=(1500, 950)):
        self.module = module
        self.viewport = viewport

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(channel="msedge", headless=True)
        self.ctx = self.browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
            accept_downloads=True,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        self.ctx.set_default_timeout(25000)
        self.downloads = []
        DL_DIR.mkdir(parents=True, exist_ok=True)
        return self

    def new_page(self, tag):
        page = self.ctx.new_page()
        page._tag = tag
        page._console = []
        page._net4xx = []
        page._netfail = []
        page.on("console", lambda m: page._console.append(f"[{m.type}] {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("response", lambda r: page._net4xx.append(f"{r.status} {r.request.method} {r.url}")
                if r.status >= 400 else None)
        page.on("requestfailed", lambda r: page._netfail.append(
            f"{r.method} {r.url} :: {r.failure or ''}"))
        page.on("download", lambda d: self._on_dl(d))
        return page

    def _on_dl(self, d):
        try:
            name = d.suggested_filename
            path = DL_DIR / f"{int(time.time()*1000)}-{name}"
            d.save_as(str(path))
            self.downloads.append({"name": name, "bytes": path.stat().st_size, "path": str(path)})
        except Exception as e:  # noqa: BLE001
            self.downloads.append({"name": getattr(d, "suggested_filename", "?"), "error": str(e)})

    def issues(self, page, clear=False):
        out = {"console": list(page._console), "http4xx": list(page._net4xx),
               "failed": list(page._netfail)}
        if clear:
            page._console.clear()
            page._net4xx.clear()
            page._netfail.clear()
        return out

    def __exit__(self, *exc):
        try:
            self.ctx.close()
        finally:
            self.browser.close()
            self._pw.stop()
        return False


def settle(page, ms=900):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def toast_text(page):
    try:
        return page.locator(".toast, .cr-toast, #toast").first.inner_text(timeout=2500)
    except Exception:
        return ""


def is_logged_in(page):
    """P05: login page contains #loginForm; app pages contain .topbar nav."""
    try:
        return page.locator("#loginForm").count() == 0
    except Exception:
        return False