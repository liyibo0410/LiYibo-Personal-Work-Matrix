"""Core LLM HTTP client with multi-endpoint failover and mock degradation."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from llm_gateway.config import GatewayConfig, build_config
from llm_gateway.cost import record_call
from llm_gateway.exceptions import LLMResponseError

logger = logging.getLogger("llm_gateway")

_MOCK_MARKER = "__mock__"


def chat_completion_json(
    messages: list[dict[str, str]],
    *,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
    fallback_base_url: str | None = None,
    max_tokens: int = 1800,
    temperature: float = 0.3,
    timeout: float = 60.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Send a JSON-mode chat completion with failover; return (parsed_json, raw_response).

    Behavior:
      - Not configured (missing base_url/api_key/model) → returns mock, no exception.
      - Primary endpoint fails → automatically retries on fallback (if configured).
      - All endpoints fail → returns mock marked with "__mock__": true.
    """
    config = build_config(
        base_url=base_url,
        api_key=api_key,
        model=model,
        fallback_base_url=fallback_base_url,
        timeout=timeout,
    )

    if not config.base_url or not config.api_key or not config.model:
        logger.warning(
            "llm_gateway: not configured (base_url=%s, api_key=%s, model=%s) — returning mock",
            bool(config.base_url),
            bool(config.api_key),
            bool(config.model),
        )
        return _build_mock_response(config.model or "unknown", reason="not_configured")

    payload = _build_payload(config.model, messages, max_tokens, temperature)

    last_error: Exception | None = None
    for endpoint_base, endpoint_key in config.endpoints:
        try:
            raw = _http_post(endpoint_base, endpoint_key, payload, config.timeout)
            content = _extract_content(raw)
            parsed = json.loads(content)
            return parsed, raw
        except (LLMResponseError, httpx.HTTPError) as exc:
            last_error = exc
            logger.warning(
                "llm_gateway: endpoint %s failed (%s), trying next",
                endpoint_base,
                exc,
            )

    logger.error("llm_gateway: all endpoints exhausted — returning mock")
    return _build_mock_response(config.model, reason="all_endpoints_failed")


# ── internal helpers ──────────────────────────────────────────────────


def _build_payload(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    if model.startswith("deepseek-v4"):
        payload["thinking"] = {"type": "disabled"}
    return payload


def _http_post(
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    url = _chat_completion_url(base_url)
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _safe_error_detail(exc.response)
        latency = (time.perf_counter() - t0) * 1000
        record_call(
            model=payload.get("model", "unknown"),
            endpoint=base_url,
            usage=None,
            latency_ms=latency,
            is_mock=False,
        )
        raise LLMResponseError(f"LLM provider returned an error: {detail}") from exc
    except httpx.HTTPError as exc:
        latency = (time.perf_counter() - t0) * 1000
        record_call(
            model=payload.get("model", "unknown"),
            endpoint=base_url,
            usage=None,
            latency_ms=latency,
            is_mock=False,
        )
        raise LLMResponseError("LLM provider request failed.") from exc

    latency = (time.perf_counter() - t0) * 1000
    raw = resp.json()
    usage = raw.get("usage")
    record_call(
        model=payload.get("model", "unknown"),
        endpoint=base_url,
        usage=usage,
        latency_ms=latency,
        is_mock=False,
    )
    return raw


def _chat_completion_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _extract_content(response_json: dict[str, Any]) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseError("LLM response did not contain message content.") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("LLM response content was empty.")
    return content


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500]
    return json.dumps(data, ensure_ascii=False)[:500]


def _build_mock_response(
    model: str,
    *,
    reason: str = "unknown",
) -> tuple[dict[str, Any], dict[str, Any]]:
    mock_content: dict[str, Any] = {
        _MOCK_MARKER: True,
        "mock_reason": reason,
        "ok": True,
        "message": f"Mock response — LLM not available ({reason})",
    }
    parsed = dict(mock_content)
    raw: dict[str, Any] = {
        "id": "mock-none",
        "model": model or "mock",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(mock_content, ensure_ascii=False),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    record_call(
        model=model or "mock",
        endpoint="mock://local",
        usage=raw["usage"],
        latency_ms=0.0,
        is_mock=True,
    )
    return parsed, raw
