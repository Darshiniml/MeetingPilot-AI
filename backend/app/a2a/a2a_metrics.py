from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class A2AMetrics:
    _instance: A2AMetrics | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self.request_count = 0
        self.fallback_count = 0
        self.success_count = 0
        self.total_latency_ms = 0.0
        self.timeout_count = 0
        self._initialized = True

    def record_request(self) -> None:
        self.request_count += 1

    def record_latency(self, latency_ms: float) -> None:
        self.total_latency_ms += latency_ms

    def record_fallback(self) -> None:
        self.fallback_count += 1

    def record_success(self) -> None:
        self.success_count += 1

    def record_timeout(self) -> None:
        self.timeout_count += 1

    def get_stats(self) -> dict[str, Any]:
        avg_latency = 0.0
        if self.request_count > 0:
            avg_latency = self.total_latency_ms / self.request_count
            
        success_rate = 1.0
        if self.request_count > 0:
            success_rate = self.success_count / self.request_count

        return {
            "a2a_requests": self.request_count,
            "fallback_count": self.fallback_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "average_latency_ms": avg_latency,
            "timeout_count": self.timeout_count
        }

    def reset(self) -> None:
        self.request_count = 0
        self.fallback_count = 0
        self.success_count = 0
        self.total_latency_ms = 0.0
        self.timeout_count = 0


def get_a2a_metrics() -> A2AMetrics:
    return A2AMetrics()
