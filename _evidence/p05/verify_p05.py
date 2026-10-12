# -*- coding: utf-8 -*-
"""P05 衡鉴 V2.1.7 —— P1 独立冒烟验证（外部 HTTP 视角）

刻意不复用项目自带的 selftest.py：从外部按真实 HTTP 打，独立取证。
覆盖：页面可达性 / 登录 / 三角色页面级权限 / 关键 API / 错误分支。
用法：
    python verify_p05.py
产出：
    verify_p05.json   结构化结果
    verify_p05.log    人读日志
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(ROOT, "projects", "p05-contract-review")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8781

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):   # noqa: D102
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def _unwrap(raw):
    """服务端统一信封 {"code":..,"data":..,"msg":..}；返回 (envelope, biz_code, data)。"""
    try:
        env = json.loads(raw.decode("utf-8"))
    except Exception:                                          # noqa: BLE001
        return None, None, None
    if isinstance(env, dict) and "code" in env and "data" in env:
        return env, env.get("code"), env.get("data")
    return env, None, env


def call(method, path, body=None, cookie=None, timeout=20):
    url = "http://127.0.0.1:%d%s" % (PORT, path)
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read()
            env, biz, payload = _unwrap(raw)
            return {"code": resp.status, "biz": biz, "data": payload,
                    "env": env, "len": len(raw),
                    "loc": resp.headers.get("Location") or "",
                    "setcookie": (resp.headers.get("Set-Cookie") or "").split(";")[0],
                    "body": raw, "ms": round((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        env, biz, payload = _unwrap(raw)
        return {"code": exc.code, "biz": biz, "data": payload, "env": env,
                "len": len(raw), "loc": exc.headers.get("Location") or "",
                "setcookie": "", "body": raw,
                "ms": round((time.time() - t0) * 1000)}
    except Exception as exc:                                   # noqa: BLE001
        return {"code": -1, "biz": None, "data": None, "env": None, "len": 0,
                "loc": "", "setcookie": "", "body": str(exc).encode("utf-8"),
                "ms": round((time.time() - t0) * 1000)}


def main():
    results = []

    def check(name, got, expect, note=""):
        ok = got == expect
        results.append({"case": name, "got": got, "expect": expect,
                        "pass": ok, "note": note})
        return ok

    from app import config as cfg_mod
    from app import store as store_mod
    from app import server as server_mod
    from mock import feishu

    cfg = cfg_mod.Config(ROOT)
    cfg.data["server"]["port"] = PORT
    for key in ("data", "uploads", "parsed", "reports", "samples"):
        cfg.path(key)
    st = store_mod.Store(cfg.db_path())
    mock_db = os.path.join(cfg.path("data"), "mock_approval.json")
    feishu.init(ROOT, mock_db, cfg.path("samples"), force_reseed=False)

    t0 = time.time()
    httpd = server_mod.serve(cfg, st)
    boot_ms = round((time.time() - t0) * 1000)
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    time.sleep(0.3)                                    # 让监听就绪

    log = []
    log.append("=" * 74)
    log.append("  P05 衡鉴 V2.1.7 独立冒烟验证  端口=%d  启动=%dms" % (PORT, boot_ms))
    log.append("=" * 74)

    try:
        # ---------- 1. 未登录：页面守卫
        log.append("\n[1] 未登录访问页面")
        for p in ("/", "/workbench", "/twin", "/rules"):
            r = call("GET", p)
            check("未登录 GET %s" % p, r["code"], 302,
                  "Location=%s" % r["loc"])
            log.append("    GET %-12s -> %s  Location=%s" % (p, r["code"], r["loc"]))
        r = call("GET", "/login")
        check("未登录 GET /login", r["code"], 200)
        log.append("    GET /login     -> %s  (%d bytes)" % (r["code"], r["len"]))

        # ---------- 2. 未登录：API
        r = call("GET", "/api/health")
        check("GET /api/health", r["code"], 200)
        health = r["data"] or {}
        log.append("    GET /api/health -> HTTP %s / biz %s  app=%s version=%s" %
                   (r["code"], r["biz"], health.get("app"), health.get("version")))
        log.append("      pdf_channels=%s  ocr=%s  gzip=%s" %
                   ((health.get("pdf_channels") or {}).get("effective"),
                    health.get("ocr_backend"), health.get("gzip")))
        log.append("      rules_types=%s" % (health.get("rules_types"),))
        log.append("      samples=%d 个  auth.accounts=%s" %
                   (len(health.get("samples") or []),
                    (health.get("auth") or {}).get("accounts")))

        r = call("GET", "/api/auth/me")
        check("未登录 /api/auth/me 被闸门拦下", r["code"], 401)
        log.append("    GET /api/auth/me -> HTTP %s  msg=%s" %
                   (r["code"], (r["env"] or {}).get("msg")))

        # ---------- 3. 登录
        log.append("\n[2] 登录与角色")
        tokens = {}
        for user, pwd, role in (("admin", "Admin@2026", "admin"),
                                ("legal", "Legal@2026", "legal"),
                                ("applicant", "Apply@2026", "applicant")):
            r = call("POST", "/api/auth/login", {"username": user, "password": pwd})
            body = r["data"] or {}
            check("登录 %s" % user, r["code"], 200)
            tokens[role] = r["setcookie"]
            log.append("    POST /api/auth/login %-9s -> HTTP %s  role=%s  cookie=%s" %
                       (user, r["code"], body.get("role"), bool(r["setcookie"])))

        # 错口令：HTTP 层状态码必须与业务 code 一致，否则前端 resp.ok 会误判成功
        r = call("POST", "/api/auth/login", {"username": "admin", "password": "wrong"})
        log.append("    POST /api/auth/login 错口令 -> HTTP %s / biz %s  msg=%s" %
                   (r["code"], r["biz"], (r["env"] or {}).get("msg")))
        check("错口令登录 HTTP 状态码", r["code"], 401,
              "业务 code=%s，HTTP 层却给了 %s" % (r["biz"], r["code"]))
        check("错口令登录 业务 code", r["biz"], 401)

        r = call("POST", "/api/auth/login", {"username": "no-such-user", "password": "x"})
        log.append("    POST /api/auth/login 不存在用户 -> HTTP %s / biz %s" %
                   (r["code"], r["biz"]))
        check("不存在用户 HTTP 状态码", r["code"], 401)

        # ---------- 4. 带 cookie 页面
        log.append("\n[3] 已登录页面（admin）")
        for p, expect in (("/", 200), ("/workbench", 200), ("/twin", 200),
                          ("/rules", 200), ("/mock", 200)):
            r = call("GET", p, cookie=tokens["admin"])
            check("admin GET %s" % p, r["code"], expect)
            log.append("    GET %-12s -> %s  (%d bytes)" % (p, r["code"], r["len"]))

        # ---------- 5. 页面级权限
        log.append("\n[4] 页面级权限隔离（/rules 仅管理员）")
        for role in ("admin", "legal", "applicant"):
            r = call("GET", "/rules", cookie=tokens[role])
            log.append("    %-9s GET /rules -> HTTP %s / biz %s" %
                       (role, r["code"], r["biz"]))
        check("legal GET /rules", call("GET", "/rules", cookie=tokens["legal"])["code"], 403)
        check("applicant GET /rules", call("GET", "/rules", cookie=tokens["applicant"])["code"], 403)

        # ---------- 6. 关键 API
        log.append("\n[5] 关键 API（admin）")
        for p, expect in (("/api/stats", 200), ("/api/cases", 200), ("/api/rules", 200),
                          ("/api/twin", 200), ("/api/queue", 200), ("/api/metrics", 200),
                          ("/api/audit", 200), ("/api/samples", 200),
                          ("/api/assistant/kb", 200), ("/api/scheduler", 200),
                          ("/api/notify/status", 200), ("/api/auth/accounts", 200)):
            r = call("GET", p, cookie=tokens["admin"])
            check("admin GET %s" % p, r["code"], expect)
            extra = ""
            if r["code"] == 200 and p == "/api/cases":
                d = r["data"]
                items = (d or {}).get("items") if isinstance(d, dict) else d
                extra = "  审查任务=%s" % (len(items) if items is not None else "-")
            if r["code"] == 200 and p == "/api/audit":
                d = r["data"] or {}
                extra = "  审计条数=%s" % len(d.get("items") or [])
            if r["code"] == 200 and p == "/api/stats":
                d = r["data"] or {}
                extra = "  keys=%s" % (sorted(d.keys())[:8] if isinstance(d, dict) else "-")
            log.append("    GET %-22s -> %s  (%d bytes)%s" % (p, r["code"], r["len"], extra))

        # ---------- 7. API 级权限
        log.append("\n[6] API 级权限")
        r = call("GET", "/api/auth/accounts", cookie=tokens["legal"])
        check("legal /api/auth/accounts", r["code"], 403)
        log.append("    legal     GET /api/auth/accounts -> %s（预期 403）" % r["code"])
        r = call("GET", "/api/auth/accounts", cookie=tokens["applicant"])
        check("applicant /api/auth/accounts", r["code"], 403)
        log.append("    applicant GET /api/auth/accounts -> %s（预期 403）" % r["code"])

        r = call("POST", "/api/cases/1/writeback", {}, cookie=tokens["applicant"])
        check("applicant 越权回写", r["code"], 403)
        log.append("    applicant POST /api/cases/1/writeback -> %s（预期 403 越权）" % r["code"])

        # ---------- 8. 模拟审批对接
        log.append("\n[7] 模拟审批系统对接")
        r = call("GET", "/mock/feishu/api/todo")
        check("GET /mock/feishu/api/todo", r["code"], 200)
        todo = r["data"] or {}
        n = len((todo.get("data", {}) or {}).get("items") or todo.get("items") or [])
        log.append("    GET /mock/feishu/api/todo -> HTTP %s  待办=%d" % (r["code"], n))

        # ---------- 9. 静态资源与 404（必须已登录后再测，否则先被闸门重定向）
        log.append("\n[8] 静态资源与 404（已登录）")
        r = call("GET", "/no-such-page-xyz", cookie=tokens["admin"])
        check("已登录 GET 不存在页面", r["code"], 404)
        log.append("    GET /no-such-page-xyz -> %s（预期 404）" % r["code"])
        r = call("GET", "/assets/", cookie=tokens["admin"])
        log.append("    GET /assets/          -> %s" % r["code"])

    finally:
        httpd.shutdown()
        httpd.server_close()

    passed = sum(1 for x in results if x["pass"])
    total = len(results)
    log.append("")
    log.append("─" * 74)
    log.append("  结果：%d / %d 通过    服务启动耗时 %d ms" % (passed, total, boot_ms))
    log.append("─" * 74)
    for x in results:
        if not x["pass"]:
            log.append("  [失败] %s  实测=%s 预期=%s  %s" %
                       (x["case"], x["got"], x["expect"], x["note"]))

    rep = {"project": "p05-contract-review", "app": health.get("app") or "衡鉴 V2.1.7",
           "port": PORT, "boot_ms": boot_ms, "passed": passed, "total": total,
           "cases": results, "health": {k: v for k, v in health.items()
                                        if k not in ("samples",)}}

    p_json = os.path.join(OUT_DIR, "verify_p05.json")
    p_log = os.path.join(OUT_DIR, "verify_p05.log")
    with io.open(p_json, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2, default=str)

    text = "\n".join(str(x) for x in log)
    if not text.endswith("\n"):
        text += "\n"
    with io.open(p_log, "w", encoding="utf-8") as fh:
        fh.write(text)

    with io.open(os.path.join(OUT_DIR, "_stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write("RESULT %d/%d boot=%dms\n" % (passed, total, boot_ms))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
