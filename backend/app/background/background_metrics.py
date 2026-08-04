from __future__ import annotations

import time
from threading import RLock

class BackgroundMetrics:
    """Thread-safe statistics counter for background agent utilization telemetry."""
    
    def __init__(self) -> None:
        self.start_time = time.perf_counter()
        self.events_processed = 0
        self.errors_count = 0
        self.restarts_count = 0
        self.recovery_attempts = 0
        self.cpu_usage = 0.0
        self.memory_usage_mb = 0.0
        self.module_health: dict[str, str] = {}
        self._lock = RLock()

    def increment_events(self) -> None:
        with self._lock:
            self.events_processed += 1

    def increment_errors(self) -> None:
        with self._lock:
            self.errors_count += 1

    def increment_restarts(self) -> None:
        with self._lock:
            self.restarts_count += 1

    def increment_recovery_attempts(self) -> None:
        with self._lock:
            self.recovery_attempts += 1

    def update_resources(self, cpu: float, memory: float) -> None:
        with self._lock:
            self.cpu_usage = cpu
            self.memory_usage_mb = memory

    def update_module_health(self, module_name: str, status: str) -> None:
        with self._lock:
            self.module_health[module_name] = status

    def get_uptime(self) -> float:
        return time.perf_counter() - self.start_time

    def serialize(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": self.get_uptime(),
                "events_processed": self.events_processed,
                "errors": self.errors_count,
                "restarts": self.restarts_count,
                "recovery_attempts": self.recovery_attempts,
                "cpu_usage_percent": self.cpu_usage,
                "memory_usage_mb": self.memory_usage_mb,
                "modules": dict(self.module_health)
            }
