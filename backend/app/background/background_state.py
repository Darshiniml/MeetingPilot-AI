from __future__ import annotations

import logging
from enum import Enum
from datetime import datetime, timezone
from threading import RLock

logger = logging.getLogger(__name__)

class BackgroundState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    ERROR = "ERROR"

class BackgroundStateManager:
    """Thread-safe manager for tracking Background Desktop Agent lifecycle transitions."""
    
    def __init__(self) -> None:
        self._state = BackgroundState.STOPPED
        self._previous_state = BackgroundState.STOPPED
        self._last_changed = datetime.now(timezone.utc)
        self._lock = RLock()

    def get_state(self) -> BackgroundState:
        with self._lock:
            return self._state

    def get_previous_state(self) -> BackgroundState:
        with self._lock:
            return self._previous_state

    def get_last_changed(self) -> datetime:
        with self._lock:
            return self._last_changed

    def transition_to(self, new_state: BackgroundState, correlation_id: str | None = None, error_details: str | None = None) -> float:
        """Transitions state, logs metadata, and returns elapsed seconds in previous state."""
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._state == new_state:
                return 0.0
                
            old_state = self._state
            self._previous_state = old_state
            self._state = new_state
            elapsed_seconds = (now - self._last_changed).total_seconds()
            self._last_changed = now
            
        # Structured structured logging with duration
        log_meta = {
            "timestamp": now.isoformat(),
            "prev_state": old_state.value,
            "new_state": new_state.value,
            "duration_seconds": elapsed_seconds,
            "correlation_id": correlation_id
        }
        if error_details:
            log_meta["error"] = error_details
            
        logger.info("[Background Agent] Lifecycle State Transition: %s", log_meta)
        return elapsed_seconds
