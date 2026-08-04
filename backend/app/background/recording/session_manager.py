from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from threading import RLock
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_name: str
    description: str

class PipelineSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: int | None = None
    platform: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    recording_state: str = "IDLE"  # IDLE, RECORDING, PAUSED, STOPPED
    pipeline_state: str = "WAITING"  # WAITING, STARTING, RECORDING, TRANSCRIBING, ANALYZING, SUMMARIZING, COMPLETED, FAILED, RECOVERING
    modules_health: dict[str, str] = Field(default_factory=lambda: {
        "audio": "healthy",
        "whisper": "healthy",
        "vision": "healthy",
        "copilot": "healthy",
        "workflows": "healthy",
        "memory": "healthy"
    })
    timeline: list[TimelineEvent] = Field(default_factory=list)

class SessionManager:
    """Manages active and previous pipeline recording session states and timeline events."""
    
    def __init__(self) -> None:
        self._active_session: PipelineSession | None = None
        self._previous_sessions: dict[str, PipelineSession] = {}
        self._lock = RLock()

    def create_session(self, platform: str, meeting_id: int | None = None) -> PipelineSession:
        """Create a new active pipeline session."""
        with self._lock:
            # If there's an existing active session, save it to history before overwriting
            if self._active_session:
                self._previous_sessions[self._active_session.session_id] = self._active_session
                
            session = PipelineSession(
                platform=platform,
                meeting_id=meeting_id,
                pipeline_state="WAITING"
            )
            self._active_session = session
            self.add_timeline_event("SessionCreated", f"Session initialized for platform: {platform}")
            return session

    def get_active_session(self) -> PipelineSession | None:
        with self._lock:
            return self._active_session

    def update_pipeline_state(self, new_state: str) -> None:
        with self._lock:
            if self._active_session:
                old_state = self._active_session.pipeline_state
                self._active_session.pipeline_state = new_state
                self.add_timeline_event("StateTransition", f"Transitioned from {old_state} to {new_state}")
                logger.info("[SessionManager] Pipeline state: %s -> %s", old_state, new_state)

    def update_module_health(self, module: str, status: str) -> None:
        with self._lock:
            if self._active_session:
                self._active_session.modules_health[module] = status
                logger.info("[SessionManager] Module '%s' health updated to %s", module, status)

    def add_timeline_event(self, name: str, description: str) -> None:
        with self._lock:
            if self._active_session:
                evt = TimelineEvent(event_name=name, description=description)
                self._active_session.timeline.append(evt)

    def close_session(self) -> None:
        """Move the active session to the previous list and mark as completed."""
        with self._lock:
            if self._active_session:
                self._active_session.end_time = datetime.now(timezone.utc)
                self._active_session.recording_state = "STOPPED"
                self._active_session.pipeline_state = "COMPLETED"
                self.add_timeline_event("SessionClosed", "Recording session shut down successfully.")
                self._previous_sessions[self._active_session.session_id] = self._active_session
                self._active_session = None

    def recover_session(self, session: PipelineSession) -> None:
        """Used to restore a session state after service restart."""
        with self._lock:
            self._active_session = session
            self.add_timeline_event("SessionRecovered", "Restored active pipeline state after background agent restart.")
            logger.info("[SessionManager] Recovered pipeline session: %s", session.session_id)

    def get_session_history(self) -> list[PipelineSession]:
        with self._lock:
            return list(self._previous_sessions.values())
