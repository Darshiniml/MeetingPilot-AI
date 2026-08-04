from __future__ import annotations

import logging
from typing import Any
from app.background import get_background_service, BackgroundState

logger = logging.getLogger(__name__)

class AgentStatusService:
    """Computes running agent lifecycle states (Initializing, Running, Waiting for Meeting, etc.)."""
    
    def __init__(self) -> None:
        pass

    def get_lifecycle_state(self) -> str:
        """Resolve current background service module status into unified lifecycle state string."""
        bg_service = get_background_service()
        state = bg_service.state_manager.get_state()

        if state == BackgroundState.STARTING:
            return "Initializing"
        elif state == BackgroundState.STOPPED:
            return "Idle"
        elif state == BackgroundState.PAUSED:
            return "Paused"
        elif state == BackgroundState.ERROR:
            return "Error"

        # If Running, check the active recording pipeline states
        recording_session = bg_service.recording_manager.session_manager.get_active_session()
        if not recording_session:
            # Check meeting detector state
            md_state = bg_service.meeting_detector.current_state if hasattr(bg_service.meeting_detector, "current_state") else "IDLE"
            if hasattr(md_state, "value"):
                md_state = md_state.value
            if str(md_state).upper() in ("DETECTED", "WAITING_CONFIRMATION"):
                return "Meeting Detected"
            return "Waiting for Meeting"

        # Check active session pipeline states: WAITING, STARTING, RECORDING, TRANSCRIBING, ANALYZING, SUMMARIZING, COMPLETED, FAILED, RECOVERING
        pipeline_state = recording_session.pipeline_state
        if pipeline_state == "STARTING":
            return "Recording"
        elif pipeline_state == "TRANSCRIBING":
            return "Transcribing"
        elif pipeline_state == "ANALYZING":
            # Check if there are approvals pending
            autonomy_engine = bg_service.autonomy_engine
            if autonomy_engine and autonomy_engine.loop.approval_engine.get_pending_approvals():
                return "Waiting Approval"
            return "Analyzing"
        elif pipeline_state == "RECORDING":
            return "Recording"
        elif pipeline_state == "SUMMARIZING":
            return "Summarizing"
        elif pipeline_state == "RECOVERING":
            return "Error"

        return "Running"
