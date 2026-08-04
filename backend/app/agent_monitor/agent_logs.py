from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)

class DequeLogHandler(logging.Handler):
    """Thread-safe logging.Handler that collects logs in an in-memory buffer of limited size."""
    
    def __init__(self, maxlen: int = 1000) -> None:
        super().__init__()
        self.buffer: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = RLock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "severity": record.levelno
            }
            with self._lock:
                self.buffer.append(log_entry)
        except Exception:
            self.handleError(record)

    def get_logs(
        self,
        module: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._lock:
            logs = list(self.buffer)

        # Apply filters
        if module:
            logs = [l for l in logs if module.lower() in l["module"].lower()]
        if severity:
            logs = [l for l in logs if l["level"].upper() == severity.upper()]
        if search:
            logs = [l for l in logs if search.lower() in l["message"].lower()]

        return logs[-limit:]

    def clear(self) -> None:
        with self._lock:
            self.buffer.clear()

# Initialize global handler and attach to root logger
global_log_handler = DequeLogHandler()
logging.getLogger().addHandler(global_log_handler)
logger.info("[AgentMonitor] Global DequeLogHandler attached successfully.")
