"""Per-call cost / latency tracking for LLM gateway invocations."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("llm_gateway.cost")


@dataclass(frozen=True)
class CallRecord:
    model: str
    endpoint: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    is_mock: bool


@dataclass
class CostReport:
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    mock_calls: int = 0
    calls_by_model: dict[str, int] = field(default_factory=dict)


class _CostTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[CallRecord] = []
        self._report = CostReport()

    def record(
        self,
        *,
        model: str,
        endpoint: str,
        usage: dict[str, Any] | None,
        latency_ms: float,
        is_mock: bool,
    ) -> None:
        prompt_tokens = (usage or {}).get("prompt_tokens", 0)
        completion_tokens = (usage or {}).get("completion_tokens", 0)
        total_tokens = (usage or {}).get("total_tokens", 0)

        rec = CallRecord(
            model=model,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            is_mock=is_mock,
        )
        logger.info(
            "llm_gateway call | model=%s endpoint=%s tokens=%s latency=%.0fms mock=%s",
            model,
            endpoint,
            total_tokens,
            latency_ms,
            is_mock,
        )

        with self._lock:
            self._records.append(rec)
            r = self._report
            r.total_calls += 1
            r.total_prompt_tokens += prompt_tokens
            r.total_completion_tokens += completion_tokens
            r.total_tokens += total_tokens
            r.total_latency_ms += latency_ms
            r.mock_calls += int(is_mock)
            r.calls_by_model[model] = r.calls_by_model.get(model, 0) + 1

    def snapshot(self) -> CostReport:
        with self._lock:
            return CostReport(
                total_calls=self._report.total_calls,
                total_prompt_tokens=self._report.total_prompt_tokens,
                total_completion_tokens=self._report.total_completion_tokens,
                total_tokens=self._report.total_tokens,
                total_latency_ms=self._report.total_latency_ms,
                mock_calls=self._report.mock_calls,
                calls_by_model=dict(self._report.calls_by_model),
            )


_tracker = _CostTracker()

record_call = _tracker.record
get_cost_report = _tracker.snapshot
