"""Lightweight, thread-safe counters for autonomous agent activity."""

from __future__ import annotations

from collections import Counter
from threading import Lock


class AgentEventMetrics:
    COUNTERS = ("events_processed", "planner_calls", "tool_executions", "memory_hits", "memory_misses", "pending_approvals", "autonomous_recommendations")

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, counter: str, amount: int = 1) -> None:
        if counter not in self.COUNTERS:
            raise ValueError(f"Unknown event metric: {counter}")
        with self._lock:
            self._counts[counter] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {counter: self._counts[counter] for counter in self.COUNTERS}
