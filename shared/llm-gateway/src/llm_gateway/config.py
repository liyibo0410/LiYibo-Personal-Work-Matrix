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
    timeout: float = 60.0

    @property
    def endpoints(self) -> list[tuple[str, str]]:
        """Return ordered (base_url, api_key) pairs — primary first, fallback second."""
        pairs: list[tuple[str, str]] = [(self.base_url, self.api_key)]
        if self.fallback_base_url:
            pairs.append((self.fallback_base_url, self.api_key))
        return pairs


def build_config(
    *,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
    fallback_base_url: str | None = None,
    timeout: float = 60.0,
) -> GatewayConfig:
    """Build a GatewayConfig from nullable values, reading fallback from env if not given."""
    if not fallback_base_url:
        fallback_base_url = environ.get("LLM_BASE_URL_FALLBACK", "")
    return GatewayConfig(
        base_url=base_url or "",
        api_key=api_key or "",
        model=model or "",
        fallback_base_url=fallback_base_url or "",
        timeout=timeout,
    )
