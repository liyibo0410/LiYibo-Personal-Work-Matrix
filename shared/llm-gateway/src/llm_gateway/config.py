"""Gateway configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from os import environ


@dataclass(frozen=True)
class GatewayConfig:
    """Immutable snapshot of endpoint credentials for one chat-completion call."""

    base_url: str
    api_key: str
    model: str
    fallback_base_url: str = ""
    fallback_api_key: str = ""
    timeout: float = 60.0

    @property
    def endpoints(self) -> list[tuple[str, str]]:
        """Return ordered (base_url, api_key) pairs — primary first, fallback second.

        百炼的三套凭证互相隔离（sk-/sk-sp-/sk-ws- 各认自己的端点），备用端点必须配它自己的
        Key；未显式给 fallback key 时才复用主 Key（同厂商换 Base URL 的场景）。
        """
        pairs: list[tuple[str, str]] = [(self.base_url, self.api_key)]
        if self.fallback_base_url:
            pairs.append((self.fallback_base_url, self.fallback_api_key or self.api_key))
        return pairs


def build_config(
    *,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
    fallback_base_url: str | None = None,
    fallback_api_key: str | None = None,
    timeout: float = 60.0,
) -> GatewayConfig:
    """Build a GatewayConfig from nullable values, reading fallback from env if not given."""
    if not fallback_base_url:
        fallback_base_url = environ.get("LLM_BASE_URL_FALLBACK", "")
    if not fallback_api_key:
        fallback_api_key = environ.get("LLM_API_KEY_FALLBACK", "")
    return GatewayConfig(
        base_url=base_url or "",
        api_key=api_key or "",
        model=model or "",
        fallback_base_url=fallback_base_url or "",
        fallback_api_key=fallback_api_key or "",
        timeout=timeout,
    )
