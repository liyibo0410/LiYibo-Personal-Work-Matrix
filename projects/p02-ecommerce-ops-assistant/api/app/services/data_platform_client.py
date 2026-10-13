# -*- coding: utf-8 -*-
"""P06 数据中台客户端（跨模块真实 HTTP 调用）。

落实架构规范「P02 取 P06 指标必须走真实 HTTP 调用，端口从 SERVICE_REGISTRY 解析」：
  * 目标地址由 ``cloudpivot_config.api_url("p06", ...)`` 解析，**不硬编码端口**；
  * 任何失败（P06 未启动 / 超时 / 非 2xx / 结构异常）都走**降级**：返回
    ``{"ok": False, "degraded": True, "error": ...}``，由调用方在 UI 明确标注，
    绝不把降级结果伪装成真实数据（红线：mock/降级须双处标注）。
"""
from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from cloudpivot_config import api_url as _api_url
except Exception:                                    # noqa: BLE001
    _api_url = None

# 单次跨模块调用超时（秒）：连接 + 读取
_TIMEOUT = float(os.environ.get("P06_CLIENT_TIMEOUT", "5"))


def _base_url() -> str:
    """P06 指标接口地址，从 SERVICE_REGISTRY 解析。

    优先级：``CP_P06_METRICS_URL`` 显式覆盖（用于降级演练 / 联调指定实例）
    → SERVICE_REGISTRY（``cloudpivot_config``）→ 环境变量兜底。
    三者都不硬编码其他模块端口。
    """
    override = os.environ.get("CP_P06_METRICS_URL")
    if override:
        return override
    if _api_url is not None:
        return _api_url("p06", "/metrics/summary")
    # 兜底：注册表不可用时用环境变量（仍不硬编码端口）
    host = os.environ.get("P06_HOST", "127.0.0.1")
    port = os.environ.get("P06_PORT", "8060")
    return "http://%s:%s/api/v1/metrics/summary" % (host, port)


def fetch_metrics_summary(start_date: str | None = None,
                          end_date: str | None = None) -> dict[str, Any]:
    """拉取 P06 全量指标最新汇总。

    成功：``{"ok": True, "source": "p06-live", "url": ..., "metrics": [ {code,name,unit,latest,avg,trend}, ... ]}``
    降级：``{"ok": False, "degraded": True, "source": "unavailable", "error": ...}``
    """
    url = _base_url()
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    try:
        resp = httpx.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        return {"ok": False, "degraded": True, "source": "unavailable",
                "url": url, "error": "P06 数据中台不可达：%s" % exc}
    except ValueError as exc:
        return {"ok": False, "degraded": True, "source": "unavailable",
                "url": url, "error": "P06 返回非 JSON：%s" % exc}

    # P06 统一响应包：{code:0, data:[...], msg:"success"}
    if not isinstance(payload, dict) or payload.get("code") != 0:
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": "P06 返回异常包：%s" % (payload.get("msg") if isinstance(payload, dict) else payload)}
    data = payload.get("data")
    if not isinstance(data, list):
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": "P06 data 字段非列表"}
    return {"ok": True, "degraded": False, "source": "p06-live", "url": url, "metrics": data}


def health() -> dict[str, Any]:
    """探测 P06 是否在线（供看板标注数据来源状态）。"""
    try:
        from cloudpivot_config import api_url
        url = api_url("p06", "/health")
    except Exception:                                # noqa: BLE001
        url = "http://%s:%s/api/v1/health" % (os.environ.get("P06_HOST", "127.0.0.1"),
                                              os.environ.get("P06_PORT", "8060"))
    try:
        resp = httpx.get(url, timeout=_TIMEOUT)
        return {"ok": resp.status_code == 200, "status_code": resp.status_code, "url": url}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "url": url}
