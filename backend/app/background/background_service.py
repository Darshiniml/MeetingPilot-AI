from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.agent.events.event_bus import EventBus
from app.background.background_state import BackgroundState, BackgroundStateManager
from app.background.background_metrics import BackgroundMetrics
from app.background.startup_manager import StartupManager
from app.background.system_monitor import SystemMonitor
from app.background.hotkey_manager import HotkeyManager
from app.background.tray_service import TrayService
from app.background.background_events import (
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentPausedEvent,
    AgentResumedEvent,
    RecordingStartedEvent,
    RecordingStoppedEvent,
    HealthChangedEvent
)

logger = logging.getLogger(__name__)

class BackgroundConfigManager:
    """Isolates background configuration settings from core domain setups."""
    
    def __init__(self) -> None:
        self.start_with_windows = False
        self.enable_system_tray = True
        self.enable_global_hotkeys = True
        self.enable_system_monitoring = True
        self.logging_level = "INFO"

class BackgroundModule:
    """Interface protocol requirements for pluggable background modules."""
    
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

class BackgroundService:
    """Orchestrator singleton coordinating background agent lifecycles, modules recovery, and logging."""
    
    _instance: BackgroundService | None = None
    _lock = RLock()

    @classmethod
    def get_instance(cls) -> BackgroundService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        # Enforce singleton construction rule
        if BackgroundService._instance is not None:
            raise RuntimeError("Use BackgroundService.get_instance() to resolve background service orchestrator.")
            
        self.state_manager = BackgroundStateManager()
        self.metrics = BackgroundMetrics()
        self.config = BackgroundConfigManager()
        self.startup_manager = StartupManager()
        self.event_bus = EventBus()
        
        # Registry for pluggable background modules
        self._modules: dict[str, Any] = {}
        self._module_lock = RLock()
        self.last_heartbeat: datetime | None = None
        self.last_error: str | None = None
        
        # Infrastructure services
        self.monitor = SystemMonitor(self.event_bus, self.metrics)
        self.hotkey_manager = HotkeyManager()
        self.tray = TrayService(self)

    def register_module(self, name: str, module: Any) -> None:
        """Register a pluggable module dynamically."""
        with self._module_lock:
            self._modules[name] = module
            self.metrics.update_module_health(name, "registered")
        logger.info("[Background Agent] Module registered dynamically: %s", name)

    def start(self) -> None:
        """Start the background service runtime and load modules with fault isolation."""
        trace_id = str(uuid.uuid4())
        logger.info("[Background Agent] Startup sequence initiated. TraceId: %s", trace_id)
        
        self.state_manager.transition_to(BackgroundState.STARTING, correlation_id=trace_id)
        
        # Configure Startup settings
        if self.config.start_with_windows:
            self.startup_manager.enable_startup()
        else:
            self.startup_manager.disable_startup()
            
        # Start infrastructure services based on config
        if self.config.enable_system_monitoring:
            self.monitor.start()
        if self.config.enable_global_hotkeys:
            self.hotkey_manager.start()
            self._register_default_hotkeys()
        if self.config.enable_system_tray:
            self.tray.start()

        # Load pluggable background modules with fault isolation
        with self._module_lock:
            for name, mod in list(self._modules.items()):
                try:
                    logger.info("Initializing module: %s", name)
                    if hasattr(mod, "start"):
                        mod.start()
                    self.metrics.update_module_health(name, "running")
                except Exception as e:
                    self.metrics.increment_recovery_attempts()
                    self.metrics.update_module_health(name, "failed")
                    self.last_error = str(e)
                    logger.error("[Background Agent] Isolate failure on module '%s': %s", name, e)

        self.state_manager.transition_to(BackgroundState.RUNNING, correlation_id=trace_id)
        self.last_heartbeat = datetime.now(timezone.utc)
        
        # Publish Agent Started event
        self.event_bus.publish(AgentStartedEvent(user_id=1))
        self.metrics.increment_events()

    def stop(self) -> None:
        """Gracefully stop the background service runtime and unload modules."""
        trace_id = str(uuid.uuid4())
        logger.info("[Background Agent] Shutdown sequence initiated. TraceId: %s", trace_id)
        
        self.state_manager.transition_to(BackgroundState.SHUTTING_DOWN, correlation_id=trace_id)
        
        # Stop infrastructure services
        self.monitor.stop()
        self.hotkey_manager.stop()
        self.tray.stop()

        # Stop pluggable background modules with fault isolation
        with self._module_lock:
            for name, mod in list(self._modules.items()):
                try:
                    logger.info("Unloading module: %s", name)
                    if hasattr(mod, "stop"):
                        mod.stop()
                    self.metrics.update_module_health(name, "stopped")
                except Exception as e:
                    self.metrics.increment_errors()
                    logger.error("[Background Agent] Error stopping module '%s': %s", name, e)

        self.state_manager.transition_to(BackgroundState.STOPPED, correlation_id=trace_id)
        
        # Publish Agent Stopped event
        self.event_bus.publish(AgentStoppedEvent(user_id=1))
        self.metrics.increment_events()

    def pause(self) -> None:
        """Pause the background agent processing."""
        if self.state_manager.get_state() != BackgroundState.RUNNING:
            return
            
        trace_id = str(uuid.uuid4())
        self.state_manager.transition_to(BackgroundState.PAUSED, correlation_id=trace_id)
        self.tray.update_menu_state(is_paused=True, is_recording=False)
        
        self.event_bus.publish(AgentPausedEvent(user_id=1))
        self.metrics.increment_events()

    def resume(self) -> None:
        """Resume the background agent processing."""
        if self.state_manager.get_state() != BackgroundState.PAUSED:
            return
            
        trace_id = str(uuid.uuid4())
        self.state_manager.transition_to(BackgroundState.RUNNING, correlation_id=trace_id)
        self.tray.update_menu_state(is_paused=False, is_recording=False)
        
        self.event_bus.publish(AgentResumedEvent(user_id=1))
        self.metrics.increment_events()

    def start_recording(self) -> None:
        """Publish recording started signal."""
        logger.info("[Background Agent] Manual start recording hotkey callback.")
        self.event_bus.publish(RecordingStartedEvent(user_id=1))
        self.metrics.increment_events()
        self.tray.update_menu_state(is_paused=self.state_manager.get_state() == BackgroundState.PAUSED, is_recording=True)

    def stop_recording(self) -> None:
        """Publish recording stopped signal."""
        logger.info("[Background Agent] Manual stop recording hotkey callback.")
        self.event_bus.publish(RecordingStoppedEvent(user_id=1))
        self.metrics.increment_events()
        self.tray.update_menu_state(is_paused=self.state_manager.get_state() == BackgroundState.PAUSED, is_recording=False)

    def get_health_status(self) -> dict[str, Any]:
        """Expose current health parameters and system monitor telemetry."""
        telemetry = self.monitor.get_system_telemetry()
        return {
            "status": self.state_manager.get_state().value,
            "uptime_seconds": self.metrics.get_uptime(),
            "cpu_usage_percent": telemetry["cpu_percent"],
            "memory_usage_mb": telemetry["memory_usage_mb"],
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_error": self.last_error,
            "metrics": self.metrics.serialize()
        }

    def _register_default_hotkeys(self) -> None:
        # Ctrl+Shift+M: Start/Stop recording toggle
        self._recording_state = False
        def toggle_rec():
            self._recording_state = not self._recording_state
            if self._recording_state:
                self.start_recording()
            else:
                self.stop_recording()
                
        self.hotkey_manager.register_hotkey("Ctrl+Shift+M", toggle_rec)
        
        # Ctrl+Shift+A: Open active dashboard simulated callback
        self.hotkey_manager.register_hotkey("Ctrl+Shift+A", lambda: logger.info("[Hotkey] Triggered Open Dashboard Action."))
        
        # Ctrl+Shift+P: Pause/Resume Agent state toggle
        def toggle_pause():
            curr = self.state_manager.get_state()
            if curr == BackgroundState.RUNNING:
                self.pause()
            elif curr == BackgroundState.PAUSED:
                self.resume()
                
        self.hotkey_manager.register_hotkey("Ctrl+Shift+P", toggle_pause)

def get_background_service() -> BackgroundService:
    """Return the shared BackgroundService singleton."""
    return BackgroundService.get_instance()
