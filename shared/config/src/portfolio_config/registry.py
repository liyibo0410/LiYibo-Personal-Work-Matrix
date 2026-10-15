# -*- coding: utf-8 -*-
"""李奕波个人作品矩阵统一平台 · 服务注册表（SERVICE_REGISTRY）

端口的**唯一真源**是同目录的 ``services.json``。任何模块要调用别的模块，
都必须通过本模块解析目标 base_url，**禁止硬编码端口**（见 .qoder/rules/01）。

典型用法（跨模块真实 HTTP 调用）::

    from portfolio_config import service_url, api_url

    base = service_url("p06")                 # http://127.0.0.1:8060
    metrics = api_url("p06", "/metrics")      # http://127.0.0.1:8060/api/v1/metrics

前端镜像 ``services.js`` 由 ``build_js.py`` 从同一份 services.json 生成，
不要手改 services.js（会与真源漂移）。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
# services.json 放在 shared/config/ 顶层（src 布局的上一级），便于前端与脚本共用
_REGISTRY_FILE = os.path.normpath(os.path.join(_HERE, "..", "..", "services.json"))


class ServiceNotFound(KeyError):
    """请求了注册表里不存在的模块 id。"""


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with open(_REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def registry() -> dict[str, Any]:
    """返回完整注册表字典（含 version / host / services / layers）。"""
    return _load()


def host() -> str:
    return _load().get("host", "127.0.0.1")


def services() -> dict[str, dict]:
    return _load().get("services", {})


def get(service_id: str) -> dict:
    svc = services().get(service_id)
    if svc is None:
        raise ServiceNotFound(
            "服务 %r 不在 SERVICE_REGISTRY 中；已注册：%s"
            % (service_id, ", ".join(sorted(services())))
        )
    return svc


def ids() -> list[str]:
    return sorted(services().keys())


def port(service_id: str, *, which: str = "api") -> int:
    """取端口。which=api → api_port；which=web → web_port（缺省回退 api_port）。"""
    svc = get(service_id)
    if which == "web":
        return int(svc.get("web_port") or svc.get("api_port"))
    return int(svc.get("api_port"))


def service_url(service_id: str, *, which: str = "api") -> str:
    """模块根地址，如 http://127.0.0.1:8060（不带末尾斜杠）。"""
    return "http://%s:%d" % (host(), port(service_id, which=which))


def api_url(service_id: str, path: str = "", *, which: str = "api") -> str:
    """带 api_prefix 的接口地址。path 应以 '/' 开头或为空。

    例：api_url("p06", "/metrics") → http://127.0.0.1:8060/api/v1/metrics
    """
    svc = get(service_id)
    prefix = (svc.get("api_prefix") or "").rstrip("/")
    p = "" if not path else ("/" + path.lstrip("/"))
    return "%s%s%s" % (service_url(service_id, which=which), prefix, p)


def route_path(service_id: str) -> str:
    """统一入口路由：/workspace/{route}。"""
    return "/workspace/%s" % get(service_id).get("route", service_id)


def by_layer() -> dict[str, list[str]]:
    """按 L3/L2/L1/L0 分层归组，供外壳导航与智能体矩阵渲染。"""
    out: dict[str, list[str]] = {}
    for sid, svc in services().items():
        out.setdefault(svc.get("layer", "?"), []).append(sid)
    for layer in out:
        out[layer].sort()
    return out


if __name__ == "__main__":
    # 自检：打印注册表解析结果
    print("SERVICE_REGISTRY v%s  host=%s" % (_load().get("version"), host()))
    for sid in ids():
        print("  %-4s api=%-28s web=%-28s route=%s"
              % (sid, api_url(sid), service_url(sid, which="web"), route_path(sid)))
