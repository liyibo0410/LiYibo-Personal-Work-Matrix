# -*- coding: utf-8 -*-
"""云枢智能统一平台 · 外壳网关（shell gateway）

一个纯标准库的 HTTP 服务，承担四件事：
  1. 静态托管 shell/（前端外壳）与 shared/（设计系统 + 注册表镜像），
     让 shell 能通过同源路径 /shared/... 引用 ui-kit 与 services.js；
  2. 提供**真实**统一登录接口 /api/auth/*，用 shared/auth 签发 HS256 令牌
     —— shell 登录一次拿到令牌，挂载各模块时通过 postMessage 下发；
  3. 暴露 /api/registry（SERVICE_REGISTRY），前端据此解析各模块端口，不硬编码；
  4. 暴露 /api/services/health（对各模块端口做 TCP 探测）与 /api/brand
     （读写 shared/config/brand.json，全站品牌位的唯一真源）。

启动：
    python shell/serve.py            # 默认 127.0.0.1:8800
    set CP_AUTH_SECRET=强密钥        # 生产必须设置（否则用演示弱密钥并告警）

红线：演示账号仅用于本地联调，密码写在代码里且已文档化；生产必须接真实用户体系并设强密钥。
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# 让 `import cloudpivot_auth` / `cloudpivot_config` 可用（源码路径复用，未安装也能跑）
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_REPO, "shared", "auth", "src"),
           os.path.join(_REPO, "shared", "config", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cloudpivot_auth import (            # noqa: E402
    AuthError, issue_token, parse_bearer, verify_token,
)
import cloudpivot_config as cpconfig     # noqa: E402

SHELL_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(_REPO, "shared")
BRAND_FILE = os.path.join(SHARED_DIR, "config", "brand.json")
# 对外演示时的模块公网地址（由 _tools/tunnel.py 写入），随探活下发给前端挂 iframe。
PUBLIC_URLS_FILE = os.environ.get(
    "CP_PUBLIC_URLS_FILE", os.path.join(_REPO, "_runtime", "tunnel", "public_urls.json"))
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8800

# 品牌位默认值：brand.json 缺字段时用它兜底，保证前端永远拿到完整结构。
DEFAULT_BRAND = {
    "company": "云枢智能",
    "name_en": "CloudPivot",
    "subtitle": "统一平台",
    "tagline": "AI 电商运营中台",
    "version": "v1.0",
    "logo": "",
    "initials": "CP",
}
# logo 以 dataURL 存进 JSON，给一个明确上限（约 4MB 文本），避免有人拖进原图把配置撑爆。
MAX_LOGO_BYTES = 4 * 1024 * 1024

# ------------------------------------------------------------------ 演示账号
# 角色对齐平台 RBAC：owner(老板) / ops(运营) / legal(法务) / sales(销售) / admin
# 密码为本地演示用途，已在 README 文档化；生产环境必须替换为真实用户体系。
DEMO_ACCOUNTS = {
    "owner":  {"password": "owner123",  "name": "张总",   "roles": ["owner"],        "title": "老板 / 全局"},
    "ops":    {"password": "ops123",    "name": "李运营", "roles": ["ops"],          "title": "电商运营"},
    "legal":  {"password": "legal123",  "name": "王法务", "roles": ["legal"],        "title": "法务合规"},
    "sales":  {"password": "sales123",  "name": "赵销售", "roles": ["sales"],        "title": "销售"},
    "admin":  {"password": "admin123",  "name": "管理员", "roles": ["admin"],        "title": "系统管理员"},
}

_CONTENT_TYPE = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".map": "application/json; charset=utf-8",
}


def read_public_urls() -> dict:
    """对外演示时各模块的公网地址（服务 id -> https 根地址）。

    没有隧道文件就返回空字典 —— 前端继续按「跟随 location.hostname」拼 host:port，
    本机与局域网演示的行为完全不变。
    """
    try:
        with open(PUBLIC_URLS_FILE, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return {}
    urls = stored.get("urls", stored) if isinstance(stored, dict) else {}
    return {k: v for k, v in urls.items()
            if isinstance(v, str) and v.startswith("https://")}


def read_brand() -> dict:
    brand = dict(DEFAULT_BRAND)
    try:
        with open(BRAND_FILE, encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            for k in DEFAULT_BRAND:
                if isinstance(stored.get(k), str):
                    brand[k] = stored[k]
    except (OSError, ValueError):
        pass
    return brand


def write_brand(patch: dict) -> tuple[bool, str]:
    """只接受白名单字段，原子写回 brand.json。返回 (成功, 错误信息)。"""
    brand = read_brand()
    for key in ("company", "name_en", "subtitle", "tagline", "version", "initials"):
        if key in patch and isinstance(patch[key], str):
            val = patch[key].strip()
            if val:
                brand[key] = val[:40]
    if "logo" in patch:
        logo = patch["logo"]
        if not isinstance(logo, str):
            return False, "logo 字段类型不对"
        if logo and not logo.startswith("data:image/"):
            # 只收图片 dataURL：外链会在离线演示时裂图，也不允许塞任意脚本。
            return False, "logo 必须是图片 dataURL"
        if len(logo.encode("utf-8")) > MAX_LOGO_BYTES:
            return False, "logo 图片过大（上限 4MB），请先压缩"
        brand["logo"] = logo
    try:
        brand["_comment"] = (
            "全平台品牌位单一真源。改这里即可全站生效；也可在外壳左下角「品牌定制」里改，"
            "写回的就是本文件。company=公司名（侧栏/登录页/浏览器标题），name_en=英文名（侧栏页脚），"
            "subtitle=侧栏副标题，tagline=登录页副标题，logo=图片 dataURL（留空则显示 initials），"
            "initials=无图时的字母标。"
        )
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(BRAND_FILE), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(brand, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, BRAND_FILE)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False, "写入失败：%s" % exc
    return True, ""


def probe_port(host: str, port: int, timeout: float = 0.35) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, int(port))) == 0


class Handler(BaseHTTPRequestHandler):
    server_version = "CloudPivotShell/1.0"

    # ---- 基础响应工具
    def _send_json(self, code, obj, cors=False):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # 只给「读品牌」开跨域：构建型模块（P01/P02/P03 的 dev server）与 file://
        # 打开的门户没有 /shared 同源映射，只能回落到网关读 brand.json。
        # brand.json 里没有任何密钥，且它本就作为 /shared/* 静态资源公开。
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self, limit: int = 1 << 20):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > limit:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except ValueError:
            return {}

    def log_message(self, fmt, *args):     # 收敛访问日志噪音
        if os.environ.get("CP_SHELL_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)

    # ---- 路由
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/auth/login":
            return self._login()
        if path == "/api/brand":
            return self._save_brand()
        self._send_json(404, {"ok": False, "error": "未知接口"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self._send_json(200, {"ok": True, "service": "shell-gateway"})
        if path == "/api/registry":
            return self._send_json(200, cpconfig.registry())
        if path == "/api/brand":
            return self._send_json(200, {"ok": True, "brand": read_brand()}, cors=True)
        if path == "/api/services/health":
            return self._services_health()
        if path == "/api/auth/verify":
            return self._verify()
        # 静态资源
        return self._serve_static(path)

    # ---- 全平台端口探活（侧栏状态点的真源）
    def _services_health(self):
        reg = cpconfig.registry()
        host = reg.get("host", "127.0.0.1")
        out = {}
        for sid, svc in reg.get("services", {}).items():
            ports = {}
            for field in ("web_port", "api_port", "commerce_port"):
                pt = svc.get(field)
                if pt and str(pt) not in ports:
                    ports[str(pt)] = probe_port(host, pt)
            # 前端端口优先决定「能不能看」；纯后端型模块（web==api）只有一个键。
            primary = str(svc.get("web_port") or svc.get("api_port"))
            out[sid] = {
                "online": bool(ports.get(primary, False)),
                "ports": ports,
            }
        self._send_json(200, {"ok": True, "host": host, "services": out,
                              "public_urls": read_public_urls(),
                              "checked_at": int(time.time())})

    # ---- 品牌接口
    def _save_brand(self):
        # 外壳默认绑 0.0.0.0（局域网可访问），写接口必须带有效令牌，
        # 否则同 WiFi 下任何人都能改公司名/logo 或往 brand.json 里塞大图。
        token = parse_bearer(self.headers.get("Authorization"))
        if not token:
            return self._send_json(401, {"ok": False, "error": "缺少令牌，请先登录外壳"})
        try:
            verify_token(token)
        except AuthError as exc:
            return self._send_json(401, {"ok": False, "error": "令牌无效：%s" % exc})
        body = self._read_body(limit=MAX_LOGO_BYTES + (1 << 20))
        if not isinstance(body, dict) or not body:
            return self._send_json(400, {"ok": False, "error": "请求体不是有效 JSON（或超出大小上限）"})
        ok, err = write_brand(body)
        if not ok:
            return self._send_json(400, {"ok": False, "error": err})
        self._send_json(200, {"ok": True, "brand": read_brand()})

    # ---- 鉴权接口
    def _login(self):
        body = self._read_body()
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        acct = DEMO_ACCOUNTS.get(username)
        if not acct or acct["password"] != password:
            return self._send_json(401, {"ok": False, "error": "用户名或密码错误"})
        token = issue_token(username, acct["roles"], ttl=8 * 3600,
                            extra={"name": acct["name"], "title": acct["title"]})
        self._send_json(200, {
            "ok": True, "token": token,
            "user": {"username": username, "name": acct["name"],
                     "roles": acct["roles"], "title": acct["title"]},
        })

    def _verify(self):
        token = parse_bearer(self.headers.get("Authorization"))
        if not token:
            return self._send_json(401, {"ok": False, "error": "缺少令牌"})
        try:
            payload = verify_token(token)
        except AuthError as exc:
            return self._send_json(401, {"ok": False, "error": str(exc)})
        self._send_json(200, {"ok": True, "payload": payload})

    # ---- 静态文件（限定 shell/ 与 shared/，防目录穿越）
    def _serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        # /shared/* → shared 目录；其余 → shell 目录
        if path.startswith("/shared/"):
            rel = path[len("/shared/"):]
            base = SHARED_DIR
        else:
            rel = path.lstrip("/")
            base = SHELL_DIR
        rel = rel.replace("\\", "/")
        full = os.path.normpath(os.path.join(base, rel))
        # 目录穿越防护：解析后必须仍在 base 内
        if not full.startswith(os.path.normpath(base)):
            return self._send_json(403, {"ok": False, "error": "禁止访问"})
        if not os.path.isfile(full):
            return self._send_json(404, {"ok": False, "error": "资源不存在：%s" % path})
        ext = os.path.splitext(full)[1].lower()
        # 白名单外的一律不发：本文件自身含演示口令，对外隧道打开时 GET /serve.py
        # 会把源码连同口令一起下载走。前端只可能需要 html/js/css/json/图片与字体。
        if ext not in _CONTENT_TYPE:
            return self._send_json(403, {"ok": False, "error": "不提供该类型文件"})
        ctype = _CONTENT_TYPE[ext]
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            return self._send_json(500, {"ok": False, "error": "读取失败"})
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def main():
    host = os.environ.get("CP_SHELL_HOST", DEFAULT_HOST)
    port = int(os.environ.get("CP_SHELL_PORT", DEFAULT_PORT))
    if not os.environ.get("CP_AUTH_SECRET"):
        sys.stderr.write("[shell] 提示：未设置 CP_AUTH_SECRET，登录令牌将使用演示弱密钥。\n")
    srv = ThreadingHTTPServer((host, port), Handler)
    print("云枢智能统一平台外壳已启动： http://%s:%d" % (host, port))
    print("演示账号：owner/owner123  ops/ops123  legal/legal123  sales/sales123  admin/admin123")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[shell] 已停止")
        srv.shutdown()


if __name__ == "__main__":
    main()
