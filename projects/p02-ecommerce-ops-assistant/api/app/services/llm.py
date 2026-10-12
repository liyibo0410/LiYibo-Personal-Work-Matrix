from typing import Any

from app.core.config import Settings
from app.services.model_settings import get_runtime_settings
from llm_gateway import chat_completion_json as _gateway_call
from llm_gateway import LLMNotConfiguredError, LLMResponseError


def is_llm_configured(settings: Settings | None = None) -> bool:
    """判断llmconfigured；集中执行业务校验、状态变更与持久化，并返回可验证结果。"""
    settings = settings or get_runtime_settings()
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


def create_json_chat_completion(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 1800,
    temperature: float = 0.3,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """创建JSON对话模型补全；委托给 shared/llm-gateway，保留原函数签名与异常类型。"""
    settings = settings or get_runtime_settings()
    fallback_url = getattr(settings, "llm_base_url_fallback", None)

    return _gateway_call(
        messages,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        fallback_base_url=fallback_url,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _post_chat_completion(
    *,
    settings: Settings,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """发送对话模型补全，委托给 llm-gateway，返回原始响应 JSON。"""
    fallback_url = getattr(settings, "llm_base_url_fallback", None)
    _, raw = _gateway_call(
        messages,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        fallback_base_url=fallback_url,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return raw


def _chat_completion_url(base_url: str) -> str:
    """对话模型补全URL，统一主流程中的格式、默认值和异常边界。"""
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _extract_message_content(response_json: dict[str, Any]) -> str:
    """提取消息内容，统一主流程中的格式、默认值和异常边界。"""
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseError("LLM response did not contain message content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("LLM response content was empty.")
    return content


__all__ = [
    "LLMNotConfiguredError",
    "LLMResponseError",
    "create_json_chat_completion",
    "is_llm_configured",
]
