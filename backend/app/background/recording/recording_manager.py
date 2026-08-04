from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.agent.events.event_bus import EventBus
from app.agent.events.event_types import EventType
from app.background.recording.recording_events import (
    RecordingStartedEvent,
    RecordingStoppedEvent,
    PipelineStartedEvent,
    PipelineCompletedEvent,
    SessionCreatedEvent,
    SessionClosedEvent
)
from app.background.recording.recording_policy import RecordingPolicy
from app.background.recording.session_manager import SessionManager, PipelineSession
from app.background.recording.pipeline_controller import PipelineController, get_background_meeting_service
from app.background.recording.recording_metrics import RecordingMetrics

logger = logging.getLogger(__name__)

class RecordingManager:
    """Orchestrates pipeline sessions and dynamic policies, responding to EventBus meeting signals."""
    
    _instance: RecordingManager | None = None
    _lock = RLock()

    @classmethod
    def get_instance(cls, event_bus: EventBus | None = None) -> RecordingManager:
        with cls._lock:
            if cls._instance is None:
                if event_bus is None:
                    raise ValueError("EventBus required to initialize RecordingManager singleton.")
                cls._instance = cls(event_bus)
            return cls._instance

    def __init__(self, event_bus: EventBus) -> None:
        if RecordingManager._instance is not None:
            raise RuntimeError("Use RecordingManager.get_instance() to resolve recording manager.")
            
        self.event_bus = event_bus
        self.session_manager = SessionManager()
        self.metrics = RecordingMetrics()
        self.policy = RecordingPolicy(mode="Autonomous")
        self.pipeline_controller = PipelineController(self.session_manager, self.metrics)
        
        self._lock = RLock()
        self._subscribe_to_events()
        self.recover_interrupted_sessions()

    def set_policy_mode(self, mode: str) -> None:
        with self._lock:
            self.policy.mode = mode
            logger.info("[RecordingManager] Updated recording policy mode to: %s", mode)

    def start_recording_pipeline(self, platform: str) -> bool:
        """Trigger start meeting recordings, checking duplicates."""
        with self._lock:
            active = self.session_manager.get_active_session()
            if active and active.recording_state == "RECORDING":
                logger.warning("[RecordingManager] Recording pipeline is already running. Ignoring start request.")
                return False
                
            session = self.session_manager.create_session(platform)
            self.event_bus.publish(SessionCreatedEvent(user_id=1, payload={"session_id": session.session_id}))
            
            # Start pipeline orchestrator
            self.event_bus.publish(PipelineStartedEvent(user_id=1))
            meeting_id = self.pipeline_controller.initialize_pipeline(platform)
            
            session.meeting_id = meeting_id
            session.recording_state = "RECORDING"
            
            self.event_bus.publish(RecordingStartedEvent(user_id=1))
            return True

    def stop_recording_pipeline(self) -> bool:
        """Trigger stop meeting recordings."""
        with self._lock:
            active = self.session_manager.get_active_session()
            if not active:
                logger.warning("[RecordingManager] No active recording session to stop.")
                return False
                
            # Stop pipeline orchestrator
            self.pipeline_controller.terminate_pipeline()
            
            self.event_bus.publish(RecordingStoppedEvent(user_id=1))
            self.event_bus.publish(PipelineCompletedEvent(user_id=1))
            
            session_id = active.session_id
            self.session_manager.close_session()
            self.event_bus.publish(SessionClosedEvent(user_id=1, payload={"session_id": session_id}))
            return True

    def recover_interrupted_sessions(self) -> None:
        """Query database for unfinished meetings and rebuild session state."""
        try:
            with get_background_meeting_service() as meeting_service:
                running_meeting = meeting_service._get_single_running_meeting()
                
            if running_meeting:
                logger.info("[RecordingManager] Unfinished meeting session detected: MeetingID %s", running_meeting.id)
                session = PipelineSession(
                    meeting_id=running_meeting.id,
                    platform="Unknown Platform",
                    recording_state="RECORDING",
                    pipeline_state="RECORDING"
                )
                self.session_manager.recover_session(session)
                self.metrics.record_recovery_attempt()
        except Exception as e:
            logger.error("[RecordingManager] Session recovery failed: %s", e)

    def _subscribe_to_events(self) -> None:
        """Listen to EventBus meeting classification messages."""
        self.event_bus.subscribe(EventType.MEETING_DETECTED, self._handle_meeting_detected)
        self.event_bus.subscribe(EventType.MEETING_STARTED, self._handle_meeting_started)
        self.event_bus.subscribe(EventType.MEETING_STOPPED, self._handle_meeting_stopped)

    def _handle_meeting_detected(self, event: Any) -> None:
        with self._lock:
            payload = event.payload or {}
            platform = payload.get("platform", "Unknown")
            confidence = payload.get("confidence", 0.0)
            threshold = 0.5 # Default threshold
            
            # Policy validation checks
            if self.policy.should_auto_start(confidence, threshold):
                logger.info("[RecordingManager] Policy allows auto-start. Starting pipeline for platform: %s", platform)
                self.start_recording_pipeline(platform)

    def _handle_meeting_started(self, event: Any) -> None:
        """Triggered when Assisted/Manual confirmation prompts are accepted."""
        with self._lock:
            payload = event.payload or {}
            platform = payload.get("platform", "Unknown")
            self.start_recording_pipeline(platform)

    def _handle_meeting_stopped(self, event: Any) -> None:
        with self._lock:
            logger.info("[RecordingManager] Signal indicates meeting stop. Terminating pipeline.")
            self.stop_recording_pipeline()
