from __future__ import annotations

import logging
from threading import RLock
from app.agent.events.event_bus import EventBus
from app.autonomy.autonomy_metrics import AutonomyMetrics
from app.autonomy.reasoning_loop import ReasoningLoop

logger = logging.getLogger(__name__)

class AutonomyEngine:
    """The brain coordinates decision-making loops and filters permissions constraints dynamically."""
    
    _instance: AutonomyEngine | None = None
    _lock = RLock()

    @classmethod
    def get_instance(cls, event_bus: EventBus | None = None) -> AutonomyEngine:
        with cls._lock:
            if cls._instance is None:
                if event_bus is None:
                    raise ValueError("EventBus required to initialize AutonomyEngine singleton.")
                cls._instance = cls(event_bus)
            return cls._instance

    def __init__(self, event_bus: EventBus) -> None:
        if AutonomyEngine._instance is not None:
            raise RuntimeError("Use AutonomyEngine.get_instance() to resolve autonomy engine.")
            
        self.event_bus = event_bus
        self.metrics = AutonomyMetrics()
        self.loop = ReasoningLoop(event_bus, self.metrics, policy_mode="Semi-Autonomous")
        self._lock = RLock()

    def start(self) -> None:
        with self._lock:
            self.loop.start()

    def stop(self) -> None:
        with self._lock:
            self.loop.stop()

    def get_health_status(self) -> dict:
        with self._lock:
            return {
                "status": "healthy" if self.loop._running else "paused",
                "running": self.loop._running,
                "policy_mode": self.loop.policy_engine.mode,
                "metrics": self.metrics.serialize()
            }
