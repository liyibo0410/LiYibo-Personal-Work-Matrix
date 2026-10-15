# -*- coding: utf-8 -*-
"""李奕波个人作品矩阵统一平台 · 外壳网关（shell gateway）

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
    set CP_OWNER_PASSWORD=私有口令   # 不设则首次启动自动生成并落盘 _runtime/owner_password.txt

红线：演示账号仅用于本地联调，密码写在代码里且已文档化；生产必须接真实用户体系并设强密钥。
"""
from __future__ import annotations

import email.utils
import gzip
import hmac
import json
import os
import secrets
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# 让 `import portfolio_auth` / `portfolio_config` 可用（源码路径复用，未安装也能跑）
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_REPO, "shared", "auth", "src"),
           os.path.join(_REPO, "shared", "config", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from portfolio_auth import (            # noqa: E402
    AuthError, issue_token, parse_bearer, require_role, verify_token,
)
import portfolio_config as cpconfig     # noqa: E402

SHELL_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(_REPO, "shared")
BRAND_FILE = os.path.join(SHARED_DIR, "config", "brand.json")
RESUME_FILE = os.path.join(SHARED_DIR, "config", "resume.json")
# 对外演示时的模块公网地址（由 _tools/tunnel.py 写入），随探活下发给前端挂 iframe。
PUBLIC_URLS_FILE = os.environ.get(
    "CP_PUBLIC_URLS_FILE", os.path.join(_REPO, "_runtime", "tunnel", "public_urls.json"))
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8800

# 品牌位默认值：brand.json 缺字段时用它兜底，保证前端永远拿到完整结构。
DEFAULT_BRAND = {
    "company": "李奕波个人作品矩阵",
    "name_en": "Li Yibo's Personal Portfolio",
    "subtitle": "统一平台",
    "tagline": "AI 电商运营中台",
    "version": "v1.0",
    "logo": "",
    "initials": "CP",
}
# logo 以 dataURL 存进 JSON，给一个明确上限（约 4MB 文本），避免有人拖进原图把配置撑爆。
MAX_LOGO_BYTES = 4 * 1024 * 1024

# 材料区默认值：resume.json 缺失/坏 JSON 时兜底，保证 GET /api/resume 永远返回完整结构。
# 内容与 index.html #lp-resume 原硬编码一致（拆分时未增删事实）。
DEFAULT_RESUME = {
    "name": "李奕波",
    "role": "独立开发 · 全栈工程",
    "pdf": "",
    "contacts": {
        "email": "2332908627@qq.com",
        "github": "github.com/liyibo0410",
        "edu": "大专 · 河南建筑职业技术学院",
        "certs": "影刀 RPA 高级工程师 · 英语四级",
    },
    "skills": [
        {"t": "RAG 全链路", "d": "文档解析 / 切分 / 向量化 / 混合检索 / 重排 / 生成 / 评测；BGE-M3、Milvus / Qdrant、RRF 融合、BGE 重排、HyDE、查询改写、引用溯源。"},
        {"t": "Agent 编排", "d": "LangChain / LangGraph，ReAct、计划执行、多子智能体协同；函数调用、MCP 工具接入、Pydantic 结构化输出校验。"},
        {"t": "工程化", "d": "Python / FastAPI 异步服务 + SSE 流式；MySQL、Redis、Docker、Linux、Git 完整工程化与云部署上线。"},
        {"t": "微调与部署", "d": "轻量化微调、训练集构建、开源模型私有化部署、vLLM 推理加速。"},
        {"t": "多模态 & 评测", "d": "视觉大模型 + OCR 识别扫描件 / 表格；Ragas 指标评测 + 兜底策略；Dify / Coze 工作流。"},
    ],
    "projects": [
        {"title": "企业运营中台 · 四层 AI 中台底座（项目负责人）",
         "desc": "自研大模型网关（多端点故障转移 / 成本统计 / 降级）、服务注册中心消除跨模块硬编码、微前端 iframe + postMessage 统一令牌与主题、DuckDB 分层数仓 + ETL 血缘 + 数据质量校验。",
         "tags": ["10 后端 + 4 前端", "506 测试", "跨模块 HTTP 真实调用 + 异常自动降级"]},
        {"title": "团队运营助手 · 多租户 AI 运营 SaaS",
         "desc": "四角色 RBAC + 路由守卫 + 按钮级权限；广告法合规引擎（108 规则、近形字 / 零宽字符 / 全角空格三级匹配、法条溯源）；LangGraph 编排多智能体（商品诊断 / 竞品分析 / 创意策划 / 经营复盘，断点恢复 + 人工审批）。",
         "tags": ["178 Pytest", "RBAC 403 已验", "合规高危拦截 100%", "F1=98.2%"]},
        {"title": "垂直场景 AI 应用套件",
         "desc": "私有知识库（双链路检索、RRF + 交叉编码精排、修复重排量纲缺陷、Ragas 忠实度 0.978）、零依赖合同审查（99ms 启动、边界条款转人工）、AI 客服（两阶段意图、防幻觉、73 Pytest）、NL2SQL（只读护栏拦截 DDL/DML、137 Pytest）。",
         "tags": ["23+15 重排单测", "48 Pytest + 66/66 自检"]},
    ],
    "education": "河南建筑职业技术学院（大专）· 专业排名第一 · 国家奖学金 · 国家励志奖学金 · 省级优秀毕业生。",
}
MAX_SKILLS = 15
MAX_PROJECTS = 15
MAX_TAGS = 8

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

# ------------------------------------------------------------------ owner 私密通道
# 根因：brand.json 是全站单一真源，而演示账号是公开的 —— 任何访客登录 admin 后
# POST /api/brand 就能改全局默认，所有人（包括作者本人）跟着变（「别人改了我这边
# 也变了」）。收权方案：全站默认的写权限只保留给一条不公开的 owner 通道，口令从
# 环境变量 CP_OWNER_PASSWORD 读取；未设置则首次启动用 secrets 生成一次、落盘
# _runtime/owner_password.txt（0600 尽力，Windows 上由 NTFS 权限兜底）。
# 红线：owner 口令绝不进 DEMO_ACCOUNTS、不进启动提示、不进前端演示账号 chips。
RUNTIME_DIR = os.path.join(_REPO, "_runtime")
OWNER_PASSWORD_FILE = os.path.join(RUNTIME_DIR, "owner_password.txt")
OWNER_SUB = "__owner__"          # owner 通道令牌的 sub，用于与演示账号的 owner 角色区分
_owner_password_cache: str | None = None


def _owner_password() -> str:
    """解析 owner 口令：环境变量优先；否则读 / 生成 _runtime/owner_password.txt。"""
    global _owner_password_cache
    if _owner_password_cache is not None:
        return _owner_password_cache
    pw = os.environ.get("CP_OWNER_PASSWORD", "").strip()
    if not pw:
        try:
            with open(OWNER_PASSWORD_FILE, encoding="utf-8") as f:
                pw = f.read().strip()
        except OSError:
            pw = ""
        if not pw:
            pw = secrets.token_urlsafe(12)
            try:
                os.makedirs(RUNTIME_DIR, exist_ok=True)
                fd = os.open(OWNER_PASSWORD_FILE,
                             os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(pw + "\n")
                print("[shell] 已自动生成 owner 口令，写入 %s（仅作者本人使用，勿提交仓库）"
                      % os.path.relpath(OWNER_PASSWORD_FILE, _REPO))
            except OSError as exc:
                print("[shell] 警告：owner 口令写盘失败（%s），本次仅内存有效，重启会再生成" % exc)
    _owner_password_cache = pw
    return pw


# owner-login 简单节流：60 秒滑窗内连续失败 ≥10 次直接拒绝，不给在线爆破留节奏。
_owner_fail_lock = threading.Lock()
_owner_fail_times: list[float] = []


def _owner_login_throttled() -> bool:
    now = time.time()
    with _owner_fail_lock:
        _owner_fail_times[:] = [t for t in _owner_fail_times if now - t < 60.0]
        return len(_owner_fail_times) >= 10

_CONTENT_TYPE = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".woff2": "font/woff2", ".map": "application/json; charset=utf-8",
}

# 静态资源缓存策略（仅作用于 _serve_static，不碰任何 /api/* 鉴权逻辑）。
# 原则：可能随时改动的入口/配置走 no-cache（保证外壳与品牌改动即时生效）；
# 指纹化、内容稳定的资源给较长 max-age，减少公网访客反复跨隧道重下载。
# 注意：标准库 http.server 不压缩，这里只加缓存头；文本类资源压缩应在 nginx 跳板层做。
_CACHE_CONTROL = {
    ".html": "no-cache",
    ".json": "no-cache",                       # shared/config/* 可能被品牌接口改写
    ".js": "public, max-age=3600",
    ".css": "public, max-age=3600",
    ".svg": "public, max-age=3600",
    ".webp": "public, max-age=3600",
    ".woff2": "public, max-age=3600",
    ".png": "public, max-age=86400",
    ".jpg": "public, max-age=86400",
    ".jpeg": "public, max-age=86400",
    ".ico": "public, max-age=86400",
    ".pdf": "public, max-age=86400",           # 大体积静态文件（PDF）走一天缓存
    ".map": "public, max-age=86400",
}


def _cache_control_for(ext: str) -> str:
    return _CACHE_CONTROL.get(ext.lower(), "no-cache")

# 静态资源缓存与压缩策略：
# - 外壳与所有模块共享的 /shared 设计系统/字体/vendor 库都从这里出，公网隧道下
#   每次刷新都重新下载是首屏慢的主因之一；加 5 分钟强缓存 + 304 条件请求可大幅减负。
# - HTML/JS/CSS/JSON/SVG 这类文本走 gzip（stdlib zlib，风险低）；已压缩的二进制
#   （png/jpg/woff2/pdf）本身不可压，跳过。nginx 若也开了 gzip 会跳过已带
#   Content-Encoding 的响应，不会二次压缩。
_STATIC_MAX_AGE = 300
_GZIP_MIN_BYTES = 1024
_GZIP_TYPES = {".html", ".js", ".css", ".json", ".svg", ".map", ".txt", ".xml"}


def _should_gzip(ext: str, data: bytes, accept_encoding: str) -> bool:
    if ext not in _GZIP_TYPES:
        return False
    if len(data) < _GZIP_MIN_BYTES:
        return False
    return "gzip" in (accept_encoding or "").lower()


def _encode_gzip(data: bytes):
    """压缩；若压完不更小则返回 None（避免徒增 CPU）。"""
    try:
        comp = gzip.compress(data, 9)
        return comp if len(comp) < len(data) else None
    except Exception:
        return None


def read_public_urls() -> dict:
    """对外演示时各模块的公网地址（服务 id -> http(s) 根地址）。

    没有隧道文件就返回空字典 —— 前端继续按「跟随 location.hostname」拼 host:port，
    本机与局域网演示的行为完全不变。

    http:// 也接受：自建服务器中转（SSH 反向隧道 + nginx 路径分流，见
    _tools/tunnel_remote.py）没有 TLS 终端，发给访客的就是 http 地址；
    只有 *.trycloudflare.com 那种 Quick Tunnel 才带 https。
    """
    try:
        with open(PUBLIC_URLS_FILE, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return {}
    urls = stored.get("urls", stored) if isinstance(stored, dict) else {}
    return {k: v for k, v in urls.items()
            if isinstance(v, str) and (v.startswith("https://") or v.startswith("http://"))}


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
    tmp = None
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
        tmp = None
    except OSError as exc:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False, "写入失败：%s" % exc
    return True, ""


def read_resume() -> dict:
    """读取材料数据真源；文件缺失/坏 JSON/字段类型不对时逐级回退到 DEFAULT_RESUME。"""
    data = json.loads(json.dumps(DEFAULT_RESUME, ensure_ascii=False))  # 深拷贝
    try:
        with open(RESUME_FILE, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return data
    if not isinstance(stored, dict):
        return data
    for key in ("name", "role", "pdf", "education"):
        if isinstance(stored.get(key), str):
            data[key] = stored[key]
    contacts = stored.get("contacts")
    if isinstance(contacts, dict):
        for key in DEFAULT_RESUME["contacts"]:
            if isinstance(contacts.get(key), str):
                data["contacts"][key] = contacts[key]
    skills = stored.get("skills")
    if isinstance(skills, list):
        cleaned = [{"t": s["t"], "d": s["d"]} for s in skills
                   if isinstance(s, dict) and isinstance(s.get("t"), str) and isinstance(s.get("d"), str)]
        data["skills"] = cleaned
    projects = stored.get("projects")
    if isinstance(projects, list):
        cleaned = []
        for p in projects:
            if not (isinstance(p, dict) and isinstance(p.get("title"), str) and isinstance(p.get("desc"), str)):
                continue
            tags = [t for t in (p.get("tags") if isinstance(p.get("tags"), list) else [])
                    if isinstance(t, str)]
            cleaned.append({"title": p["title"], "desc": p["desc"], "tags": tags})
        data["projects"] = cleaned
    return data


def write_resume(patch: dict) -> tuple[bool, str]:
    """只接受白名单字段，类型校验 + 长度上限，原子写回 resume.json。返回 (成功, 错误信息)。"""
    data = read_resume()
    for key, limit in (("name", 40), ("role", 60), ("pdf", 200), ("education", 400)):
        if key in patch:
            val = patch[key]
            if not isinstance(val, str):
                return False, "%s 字段类型不对" % key
            val = val.strip()
            if len(val) > limit:
                return False, "%s 超长（上限 %d 字）" % (key, limit)
            data[key] = val
    if "contacts" in patch:
        c = patch["contacts"]
        if not isinstance(c, dict):
            return False, "contacts 字段类型不对"
        for key in ("phone", "email", "github", "edu", "certs"):
            if key in c:
                val = c[key]
                if not isinstance(val, str):
                    return False, "contacts.%s 字段类型不对" % key
                val = val.strip()
                if len(val) > 120:
                    return False, "contacts.%s 超长（上限 120 字）" % key
                data["contacts"][key] = val
    if "skills" in patch:
        skills = patch["skills"]
        if not isinstance(skills, list) or len(skills) > MAX_SKILLS:
            return False, "skills 必须是列表且不超过 %d 条" % MAX_SKILLS
        cleaned = []
        for s in skills:
            if not (isinstance(s, dict) and isinstance(s.get("t"), str) and isinstance(s.get("d"), str)):
                return False, "skills 每条须为 {t, d} 且均为字符串"
            t, d = s["t"].strip(), s["d"].strip()
            if not t:
                return False, "skills 条目标题不能为空"
            if len(t) > 40 or len(d) > 600:
                return False, "skills 条目超长（标题 ≤40 字，描述 ≤600 字）"
            cleaned.append({"t": t, "d": d})
        data["skills"] = cleaned
    if "projects" in patch:
        projects = patch["projects"]
        if not isinstance(projects, list) or len(projects) > MAX_PROJECTS:
            return False, "projects 必须是列表且不超过 %d 条" % MAX_PROJECTS
        cleaned = []
        for p in projects:
            if not (isinstance(p, dict) and isinstance(p.get("title"), str) and isinstance(p.get("desc"), str)):
                return False, "projects 每条须为 {title, desc, tags} 且字符串字段类型正确"
            title, desc = p["title"].strip(), p["desc"].strip()
            if not title:
                return False, "projects 条目标题不能为空"
            if len(title) > 80 or len(desc) > 2000:
                return False, "projects 条目超长（标题 ≤80 字，描述 ≤2000 字）"
            tags = p.get("tags", [])
            if not isinstance(tags, list) or len(tags) > MAX_TAGS:
                return False, "projects.tags 必须是字符串列表且不超过 %d 个" % MAX_TAGS
            tags = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
            if any(len(t) > 40 for t in tags):
                return False, "projects.tags 单个标签 ≤40 字"
            cleaned.append({"title": title, "desc": desc, "tags": tags})
        data["projects"] = cleaned
    tmp = None
    try:
        data["_comment"] = (
            "材料区（外壳首页 #lp-resume）单一真源。外壳 GET /api/resume 读本文件，"
            "写入走 POST /api/resume（仅 owner 私密通道，sub==__owner__）。"
        )
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(RESUME_FILE), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, RESUME_FILE)
        tmp = None
    except OSError as exc:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False, "写入失败：%s" % exc
    return True, ""


def probe_port(host: str, port: int, timeout: float = 0.35) -> bool:
    # 正常关闭（不使用 SO_LINGER 发 RST）：曾改成 linger(1,0) 以规避探测端的 TIME_WAIT，
    # 但 P10 在那个方案下崩过一次 accept 循环（asyncio proactor WinError 64），
    # 无法排除是 RST 输入打进 uvicorn 的 accept —— 端口整洁不值得拿服务稳定性换。
    # 连接数改由 _services_health 的结果缓存来压（见 HEALTH_TTL）。
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, int(port))) == 0


# 探活结果缓存：前端每 6 秒轮询一次，每轮要做 14 次 TCP 连接，每个连接关闭后
# 在本机留一个约 120 秒的 TIME_WAIT —— 稳态就是 ~280 个临时端口被占着。
# 占满后 socket() 失败，浏览器表现为随机丢静态资源（实测 ERR_NO_BUFFER_SPACE
# 加载不到 tokens.css，整站设计令牌塌成默认样式）。服务上下线不是秒级事件，
# 缓存 30 秒足够，把稳态压到 ~56 个。
HEALTH_TTL = 30.0
_health_cache: dict[str, object] = {"ts": 0.0, "payload": None}
_health_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "Li Yibo's Personal PortfolioShell/1.0"
    # 1.0 会强制「每个静态资源一条新连接」；外壳首屏 + 十个模块 iframe 的连接数在本机
    # 足以打满临时端口（见 probe_port 注释），故走 1.1 复用连接。代价是每条响应都必须
    # 带准确 Content-Length —— 下面 _send_json / _serve_static 均已满足。
    protocol_version = "HTTP/1.1"
    timeout = 30          # 回收空闲的 keep-alive 连接，避免线程与 socket 长期挂住

    # ---- 基础响应工具
    def _send_json(self, code, obj, cors=False):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        # 较大的 JSON（/api/registry、/api/services/health）在公网隧道下做 gzip
        enc = None
        if len(body) >= _GZIP_MIN_BYTES and _should_gzip(
                ".json", body, self.headers.get("Accept-Encoding", "")):
            comp = _encode_gzip(body)
            if comp is not None:
                body, enc = comp, "gzip"
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # 只给「读品牌」开跨域：构建型模块（P01/P02/P03 的 dev server）与 file://
        # 打开的门户没有 /shared 同源映射，只能回落到网关读 brand.json。
        # brand.json 里没有任何密钥，且它本就作为 /shared/* 静态资源公开。
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        if enc:
            self.send_header("Content-Encoding", enc)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self, limit: int = 1 << 20):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        if n > limit:
            # keep-alive 下没读干净的请求体会被当成下一个请求 —— 直接断链，别把流搞脏
            self.close_connection = True
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except ValueError:
            return {}

    def _discard_body(self, limit: int = MAX_LOGO_BYTES + (1 << 20)):
        """要走「不读请求体」的分支时，必须把体吃干净，否则 keep-alive 的流会错位；
        超过上限就索性断链，不把没读完的字节留给下一个请求。"""
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return
        if n > limit:
            self.close_connection = True
            return
        try:
            self.rfile.read(n)
        except OSError:
            self.close_connection = True

    def log_message(self, fmt, *args):     # 收敛访问日志噪音
        if os.environ.get("CP_SHELL_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)

    # ---- 路由
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/auth/login":
            return self._login()
        if path == "/api/auth/owner-login":
            return self._owner_login()
        if path == "/api/brand":
            return self._save_brand()
        if path == "/api/resume":
            return self._save_resume()
        self._discard_body()
        self._send_json(404, {"ok": False, "error": "未知接口"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # GET 带体不合法但客户端真会发（curl -X GET -d），不吃掉就会污染 keep-alive 的下一条请求
        self._discard_body()
        if path == "/api/health":
            return self._send_json(200, {"ok": True, "service": "shell-gateway"})
        if path == "/api/registry":
            return self._send_json(200, cpconfig.registry())
        if path == "/api/brand":
            return self._send_json(200, {"ok": True, "brand": read_brand()}, cors=True)
        if path == "/api/resume":
            return self._send_json(200, {"ok": True, "resume": read_resume()}, cors=True)
        if path == "/api/services/health":
            return self._services_health()
        if path == "/api/auth/verify":
            return self._verify()
        # 静态资源
        return self._serve_static(path)

    # ---- 全平台端口探活（侧栏状态点的真源）
    def _services_health(self):
        now = time.time()
        with _health_lock:
            cached = _health_cache["payload"]
            if cached is None or now - float(_health_cache["ts"]) >= HEALTH_TTL:
                cached = self._probe_all()
                _health_cache["payload"] = cached
                _health_cache["ts"] = now
            payload = dict(cached)
        self._send_json(200, payload)

    @staticmethod
    def _probe_all():
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
        return {"ok": True, "host": host, "services": out,
                "public_urls": read_public_urls(),
                "checked_at": int(time.time()),
                "probe_ttl_seconds": HEALTH_TTL}

    # ---- 品牌接口
    def _save_brand(self):
        # 外壳默认绑 0.0.0.0（局域网可访问），写接口必须带有效令牌。
        # 品牌位是全站真源（公司名/logo 一改，十个模块同时变），写权限只留给 owner
        # 私密通道签发的令牌 —— 演示账号（含 admin）是公开的，谁都能登录，
        # 不能再拥有改全局默认的能力。注意 shared/auth 的 require_role 对 roles 里
        # 含 owner/admin 的令牌一律放行（其他模块依赖这个宽松语义，不能改），
        # 所以这里不走 require_role(token,"owner")，而是显式校验 sub==__owner__，
        # 确保只有 /api/auth/owner-login 签发的令牌能过。
        token = parse_bearer(self.headers.get("Authorization"))
        if not token:
            self._discard_body()
            return self._send_json(401, {"ok": False, "error": "缺少令牌，请先登录外壳"})
        try:
            payload = verify_token(token)
            if payload.get("sub") != OWNER_SUB or "owner" not in (payload.get("roles") or []):
                raise AuthError(
                    "全站品牌默认仅作品集所有者可修改（owner 私密通道）；"
                    "演示账号的修改只会保存在你自己的浏览器里")
        except AuthError as exc:
            self._discard_body()
            return self._send_json(403, {"ok": False, "error": "无权修改品牌配置：%s" % exc})
        body = self._read_body(limit=MAX_LOGO_BYTES + (1 << 20))
        if not isinstance(body, dict) or not body:
            return self._send_json(400, {"ok": False, "error": "请求体不是有效 JSON（或超出大小上限）"})
        ok, err = write_brand(body)
        if not ok:
            return self._send_json(400, {"ok": False, "error": err})
        self._send_json(200, {"ok": True, "brand": read_brand()})

    # ---- 材料接口
    def _save_resume(self):
        # 鉴权与 /api/brand 同款：写权限只留给 owner 私密通道（显式校验 sub==__owner__）。
        # 不走 require_role(token,"owner") —— shared/auth 的 require_role 对 roles 含
        # owner/admin 的令牌一律放行，挡不住公开的演示账号，这条红线不能破。
        token = parse_bearer(self.headers.get("Authorization"))
        if not token:
            self._discard_body()
            return self._send_json(401, {"ok": False, "error": "缺少令牌，请先登录外壳"})
        try:
            payload = verify_token(token)
            if payload.get("sub") != OWNER_SUB or "owner" not in (payload.get("roles") or []):
                raise AuthError(
                    "全站材料默认仅作品集所有者可修改（owner 私密通道）；"
                    "演示账号的修改只会保存在你自己的浏览器里")
        except AuthError as exc:
            self._discard_body()
            return self._send_json(403, {"ok": False, "error": "无权修改材料配置：%s" % exc})
        body = self._read_body(limit=1 << 20)
        if not isinstance(body, dict) or not body:
            return self._send_json(400, {"ok": False, "error": "请求体不是有效 JSON（或超出大小上限）"})
        ok, err = write_resume(body)
        if not ok:
            return self._send_json(400, {"ok": False, "error": err})
        self._send_json(200, {"ok": True, "resume": read_resume()})

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

    def _owner_login(self):
        """owner 私密通道：口令登录，签发可写全站品牌默认的令牌。

        该账号不进 DEMO_ACCOUNTS、不进启动提示、不进前端演示账号 chips；
        口令只存在环境变量或 _runtime/owner_password.txt 里，作者本人持有。
        """
        body = self._read_body()
        password = body.get("password") or ""
        if _owner_login_throttled():
            return self._send_json(429, {"ok": False, "error": "尝试过于频繁，请一分钟后再试"})
        expected = _owner_password()
        # 常量时间比较，避免逐字节计时侧信道；expected 为空串视为未配置，直接拒绝
        ok = bool(password) and bool(expected) and hmac.compare_digest(
            password.encode("utf-8"), expected.encode("utf-8"))
        if not ok:
            with _owner_fail_lock:
                _owner_fail_times.append(time.time())
            return self._send_json(401, {"ok": False, "error": "owner 口令错误"})
        with _owner_fail_lock:
            _owner_fail_times.clear()
        token = issue_token(OWNER_SUB, ["owner", "admin"], ttl=8 * 3600,
                            extra={"name": "作品集所有者", "title": "Owner",
                                   "via": "owner-login"})
        self._send_json(200, {
            "ok": True, "token": token,
            "user": {"username": OWNER_SUB, "name": "作品集所有者",
                     "roles": ["owner", "admin"], "title": "Owner"},
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
        base_norm = os.path.normpath(base)
        # 目录穿越防护：解析后必须仍在 base 内。用 base+分隔符比较 —— 纯 startswith
        # 会把兄弟目录（shared_backup、shell_old）也算「在里面」。
        if not (full == base_norm or full.startswith(base_norm + os.sep)):
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

        # 缓存策略：经下方 _cache_control_for 统一给出（见 _CACHE_CONTROL 常量）。
        # 关键安全点：shell/ 与 shared/ 的静态资源**未做内容哈希命名**（tokens.css、
        # ui-kit.js、services.js、brand-bridge.js 等文件名固定），绝不能给 immutable ——
        # 否则改了设计令牌/品牌后浏览器一年内都读旧值。这里一律用有界 max-age，
        # 配合下方 304 条件请求做重验证：既减少跨公网重复下载，又能在文件改动后及时生效。
        cache = _cache_control_for(ext)

        mtime = os.path.getmtime(full)
        last_modified = email.utils.formatdate(mtime, usegmt=True)
        ims = self.headers.get("If-Modified-Since")
        if ims:
            try:
                ims_dt = email.utils.parsedate_to_datetime(ims)
                if ims_dt is not None and ims_dt.timestamp() >= int(mtime):
                    self.send_response(304)
                    self.send_header("Cache-Control", cache)
                    self.send_header("Last-Modified", last_modified)
                    self.end_headers()
                    return
            except (TypeError, ValueError):
                pass

        # gzip：文本类（html/js/css/json/svg）可压；已压缩二进制（png/jpg/woff2/pdf）跳过。
        # 公网 SSH 隧道下未压缩体积直接决定首屏与接口延迟，这是最大的单一优化点。
        body = data
        enc = None
        if _should_gzip(ext, body, self.headers.get("Accept-Encoding", "")):
            comp = _encode_gzip(body)
            if comp is not None:
                body, enc = comp, "gzip"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("Last-Modified", last_modified)
        if enc:
            self.send_header("Content-Encoding", enc)
        self.end_headers()
        self.wfile.write(body)


def main():
    host = os.environ.get("CP_SHELL_HOST", DEFAULT_HOST)
    port = int(os.environ.get("CP_SHELL_PORT", DEFAULT_PORT))
    if not os.environ.get("CP_AUTH_SECRET"):
        sys.stderr.write("[shell] 提示：未设置 CP_AUTH_SECRET，登录令牌将使用演示弱密钥。\n")
    srv = ThreadingHTTPServer((host, port), Handler)
    print("李奕波个人作品矩阵统一平台外壳已启动： http://%s:%d" % (host, port))
    print("演示账号：ops/ops123  legal/legal123  sales/sales123  admin/admin123")
    # 启动即解析 owner 口令：未设 CP_OWNER_PASSWORD 且无存档时，这里会生成一次、
    # 落盘并打印唯一一次提醒；之后重启直接读文件，不再重复生成。
    if os.environ.get("CP_OWNER_PASSWORD", "").strip():
        print("[shell] owner 私密通道已启用（口令来自环境变量 CP_OWNER_PASSWORD）")
    else:
        _owner_password()
        print("[shell] owner 私密通道已启用（口令见 _runtime/owner_password.txt，"
              "或设置环境变量 CP_OWNER_PASSWORD）")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[shell] 已停止")
        srv.shutdown()


if __name__ == "__main__":
    main()
