"""P07 模型调用：统一经 `shared/llm-gateway`，记录 token 与耗时，不可用时明确降级。

主用 Key 为空时把备用端点当主用（百炼 sk- / sk-sp- 只认自己的端点），
两条凭证都不齐才降级到规则兜底，并在响应里带 `source="rule"` 与原因。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from llm_gateway import chat_completion_json
from llm_gateway.cost import get_cost_report

from app import config


@dataclass
class LLMResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "llm"  # llm | mock
    model: str = ""
    endpoint: str = ""
    reason: str = ""
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_version: str = ""


def _endpoint_host_label(base_url: str) -> str:
    return base_url.split("//")[-1].split("/")[0] if base_url else ""


def chat_json(prompt_file: str, user_content: str, *, variables: dict[str, str] | None = None,
              prefer_fast: bool = False, max_tokens: int = 900, temperature: float = 0.3,
              timeout: float = 40.0) -> LLMResult:
    """以 JSON 模式调用一次模型。prompt 从 prompts/ 版本化文件读取，变量在文件内占位。"""
    settings = config.get_settings()
    endpoint = settings.llm_endpoint(prefer_fast=prefer_fast)
    if endpoint is None:
        return LLMResult(ok=False, source="mock", reason="not_configured",
                         prompt_version=prompt_file)

    system_prompt = config.load_prompt(prompt_file)
    for key, value in (variables or {}).items():
        system_prompt = system_prompt.replace("{" + key + "}", value)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    t0 = time.perf_counter()
    parsed, raw = chat_completion_json(
        messages,
        base_url=endpoint.base_url,
        api_key=endpoint.api_key,
        model=endpoint.model,
        timeout=timeout,
    )
    latency = round((time.perf_counter() - t0) * 1000, 1)
    usage = raw.get("usage") or {}

    if parsed.get("__mock__"):
        return LLMResult(
            ok=False, source="mock", model=endpoint.model,
            endpoint=_endpoint_host_label(endpoint.base_url),
            reason=str(parsed.get("mock_reason", "unknown")), latency_ms=latency,
            prompt_version=prompt_file,
        )
    return LLMResult(
        ok=True, data=parsed, source="llm", model=raw.get("model", endpoint.model),
        endpoint=_endpoint_host_label(endpoint.base_url), latency_ms=latency,
        prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage.get("completion_tokens", 0) or 0),
        total_tokens=int(usage.get("total_tokens", 0) or 0),
        prompt_version=prompt_file,
    )


def status() -> dict[str, Any]:
    """供前端动态显示「LLM 已接入 / Mock 降级」，不再写死一个 Mock 徽章。"""
    settings = config.get_settings()
    endpoint = settings.llm_endpoint()
    return {
        "configured": endpoint is not None,
        "model": endpoint.model if endpoint else "",
        "endpoint": _endpoint_host_label(endpoint.base_url) if endpoint else "",
        "endpoint_label": endpoint.label if endpoint else "",
        "reason": "" if endpoint else "主用与备用端点凭证均不完整（.env 中 base_url/api_key/model 缺项）",
        "cost": cost_snapshot(),
    }


def cost_snapshot() -> dict[str, Any]:
    report = get_cost_report()
    return {
        "total_calls": report.total_calls,
        "total_tokens": report.total_tokens,
        "mock_calls": report.mock_calls,
        "total_latency_ms": round(report.total_latency_ms, 1),
        "calls_by_model": dict(report.calls_by_model),
    }
