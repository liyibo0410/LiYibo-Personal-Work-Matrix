# -*- coding: utf-8 -*-
"""P01 AI 客服客户端（跨模块真实 HTTP 调用）。

落实架构规范「P09 销售考核消费 P01 会话数据，必须走真实 HTTP 调用，
端口从 SERVICE_REGISTRY 解析，禁止硬编码其他模块端口」：

  * 目标地址由 ``cloudpivot_config.api_url("p01", "/chat/history")`` 解析；
  * P01 的会话历史接口为 ``GET /api/chat/history?sender_id=xxx``，按用户拉取，
    返回 ``{sender_id, messages:[{session_id, role(user|bot), text, object}]}``；
  * 本客户端把 P01 的 user/bot 角色映射为 P09 的 customer/agent，并按
    ``session_id`` 聚合成一段段会话，供 P09 质检评分消费；
  * 任何失败（P01 未启动 / 超时 / 非 2xx / 结构异常）都走**降级**：返回
    ``{"ok": False, "degraded": True, "error": ...}``，由调用方在响应与前端明确标注，
    绝不把降级结果伪装成真实会话（红线：mock/降级须双处标注）。
"""
from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from cloudpivot_config import api_url as _api_url
except Exception:                                    # noqa: BLE001
    _api_url = None

# 单次跨模块调用超时（秒）
_TIMEOUT = float(os.environ.get("P01_CLIENT_TIMEOUT", "5"))


def _history_url() -> str:
    """P01 会话历史接口地址，从 SERVICE_REGISTRY 解析。

    优先级：``CP_P01_HISTORY_URL`` 显式覆盖（降级演练 / 指定实例）
    → SERVICE_REGISTRY（``cloudpivot_config``）→ 环境变量兜底。
    三者都不硬编码其他模块端口。
    """
    override = os.environ.get("CP_P01_HISTORY_URL")
    if override:
        return override
    if _api_url is not None:
        # P01 的 api_prefix 为 /api，故此处只传 /chat/history
        return _api_url("p01", "/chat/history")
    host = os.environ.get("P01_HOST", "127.0.0.1")
    port = os.environ.get("P01_PORT", "18082")
    return "http://%s:%s/api/chat/history" % (host, port)


def health() -> dict[str, Any]:
    """探测 P01 是否在线（供 P09 标注数据来源状态）。

    注意：P01 的存活探针在根路径 ``/health``（不在 ``/api`` 前缀下），
    故用 ``service_url`` 拼根地址，而非 ``api_url``。
    """
    try:
        from cloudpivot_config import service_url
        url = service_url("p01") + "/health"
    except Exception:                                # noqa: BLE001
        url = "http://%s:%s/health" % (os.environ.get("P01_HOST", "127.0.0.1"),
                                       os.environ.get("P01_PORT", "18082"))
    try:
        resp = httpx.get(url, timeout=_TIMEOUT)
        return {"ok": resp.status_code == 200, "status_code": resp.status_code, "url": url}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "url": url}


def fetch_history(sender_id: str) -> dict[str, Any]:
    """拉取单个用户在 P01 的会话历史（原始 messages）。"""
    url = _history_url()
    try:
        resp = httpx.get(url, params={"sender_id": sender_id}, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": "P01 客服不可达：%s" % exc}
    except ValueError as exc:
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": "P01 返回非 JSON：%s" % exc}

    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": "P01 返回结构异常（缺 messages 列表）"}
    return {"ok": True, "degraded": False, "source": "p01-live", "url": url,
            "sender_id": payload.get("sender_id", sender_id),
            "messages": payload["messages"]}


def _to_p09_messages(raw_messages: list[dict]) -> list[dict[str, str]]:
    """P01 HistoryMessage → P09 Message 结构。

    P01 role: user | bot  →  P09 role: customer | agent
    仅保留文本消息（object 卡片无文本时跳过），时间戳缺失则留空由 P09 补。
    """
    out: list[dict[str, str]] = []
    for m in raw_messages:
        if not isinstance(m, dict):
            continue
        text = m.get("text")
        if not text:
            continue
        role = "customer" if m.get("role") == "user" else "agent"
        out.append({"role": role, "content": text, "timestamp": m.get("timestamp", "")})
    return out


def fetch_conversations(sender_ids: list[str]) -> dict[str, Any]:
    """跨模块拉取 P01 真实会话，按 session_id 聚合成 P09 可评分的会话列表。

    成功：``{"ok": True, "source": "p01-live", "conversations": [ {sender_id, session_id, messages}, ... ],
             "fetched_senders": [...], "empty_senders": [...]}``
    降级：``{"ok": False, "degraded": True, "source": "unavailable", "error": ...}``（不伪造会话）
    """
    conversations: list[dict[str, Any]] = []
    fetched: list[str] = []
    empty: list[str] = []
    first_error: str | None = None
    url = _history_url()

    for sid in sender_ids:
        res = fetch_history(sid)
        if not res.get("ok"):
            # 任一 sender 拉取失败即视为 P01 不可达（降级），不静默跳过
            first_error = first_error or res.get("error")
            continue
        fetched.append(sid)
        # 按 session_id 聚合
        by_session: dict[str, list[dict]] = {}
        for m in res["messages"]:
            if isinstance(m, dict):
                by_session.setdefault(m.get("session_id", "default"), []).append(m)
        if not by_session:
            empty.append(sid)
        for session_id, raw in by_session.items():
            msgs = _to_p09_messages(raw)
            if msgs:
                conversations.append({
                    "sender_id": sid,
                    "session_id": session_id,
                    "messages": msgs,
                })

    if not fetched:
        return {"ok": False, "degraded": True, "source": "unavailable", "url": url,
                "error": first_error or "未成功拉取任何 P01 会话",
                "requested_senders": list(sender_ids)}

    return {"ok": True, "degraded": False, "source": "p01-live", "url": url,
            "conversations": conversations, "fetched_senders": fetched,
            "empty_senders": empty, "error": first_error}
