"""P07 → P06 数据中台：真实 HTTP 取大盘指标，用于「素材效果 vs 店铺大盘」对比。

端口从 SERVICE_REGISTRY 解析（`cloudpivot_config.api_url`），禁止硬编码。
P06 没起来就返回 `available=false` + 原因，绝不返回编造的大盘数字。
"""
from __future__ import annotations

from typing import Any

import httpx
from cloudpivot_config import api_url

from app.db import now_iso

# 与素材投放可直接对照的大盘口径
REQUESTED_METRICS = ("conversion_rate", "traffic_uv", "avg_order_value", "gmv")


def fetch_platform_metrics(timeout: float = 4.0) -> dict[str, Any]:
    url = api_url("p06", "/metrics/summary")
    base = {"source_url": url, "fetched_at": now_iso(), "requested": list(REQUESTED_METRICS)}
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {**base, "available": False, "metrics": [],
                "reason": f"{type(exc).__name__}: {str(exc)[:160]}（P06 数据中台是否在跑？"
                          f"`python _tools\\supervisor.py status`）"}
    if body.get("code") != 0:
        return {**base, "available": False, "metrics": [], "reason": f"P06 返回错误：{body.get('message', body)}"}

    picked = [
        {"code": m["code"], "name": m.get("name", m["code"]), "unit": m.get("unit", ""),
         "latest": m.get("latest"), "avg": m.get("avg"), "trend": m.get("trend")}
        for m in (body.get("data") or []) if m.get("code") in REQUESTED_METRICS
    ]
    return {**base, "available": True, "metrics": picked,
            "note": "真实跨模块调用：P07 → P06 /api/v1/metrics/summary"}
