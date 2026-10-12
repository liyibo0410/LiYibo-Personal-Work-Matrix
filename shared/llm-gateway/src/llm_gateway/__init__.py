"""llm-gateway: unified LLM HTTP client with failover, cost tracking, and mock degradation."""

from llm_gateway.client import GatewayConfig, chat_completion_json
from llm_gateway.cost import CostReport, get_cost_report
from llm_gateway.exceptions import LLMNotConfiguredError, LLMResponseError

__all__ = [
    "GatewayConfig",
    "chat_completion_json",
    "LLMNotConfiguredError",
    "LLMResponseError",
    "CostReport",
    "get_cost_report",
]
