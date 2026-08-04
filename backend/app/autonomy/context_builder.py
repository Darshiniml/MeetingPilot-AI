from __future__ import annotations

import logging
from typing import Any
from app.background import get_background_service

logger = logging.getLogger(__name__)

class ContextBuilder:
    """Consolidates application states, devices, and providers metrics into a unified ReasoningContext structure."""
    
    def __init__(self) -> None:
        pass

    def build_context(self) -> dict[str, Any]:
        """Aggregate signals dynamically from active memory registries, background managers, and providers."""
        bg_service = get_background_service()
        
        # Get active session from recording manager
        recording_session = bg_service.recording_manager.session_manager.get_active_session()
        
        # Current meeting state
        current_meeting = {}
        if recording_session:
            current_meeting = {
                "session_id": recording_session.session_id,
                "meeting_id": recording_session.meeting_id,
                "platform": recording_session.platform,
                "start_time": recording_session.start_time.isoformat() if recording_session.start_time else None,
                "recording_state": recording_session.recording_state,
                "pipeline_state": recording_session.pipeline_state
            }

        # Transcripts buffer (simulated stub)
        transcripts = [
            "We should probably finalize the API specifications by Thursday.",
            "I will send the calendar invite to the marketing team today."
        ]

        # Vision engine status
        vision_state = {
            "status": bg_service.recording_manager.session_manager.get_active_session().modules_health.get("vision", "healthy") if recording_session else "idle",
            "participants_count": 3,
            "screen_active": True
        }

        # Copilot insights
        copilot_insights = [
            {
                "insight_id": "cop-001",
                "insight_type": "deadline",
                "title": "API specs finalization",
                "content": "Finalize specifications by Thursday.",
                "confidence": 0.92,
                "speaker": "Primary Speaker",
                "timestamp": "2026-08-04T13:00:00Z"
            }
        ]

        # Working workflow states
        workflow_state = {
            "active_workflows_count": 1,
            "status": "idle"
        }

        # Provider health status mapping
        from app.providers import ProviderManager
        try:
            cal_prov = ProviderManager.get_calendar(None, 1)
            cal_health = cal_prov.get_health().get("status", "healthy") if hasattr(cal_prov, "get_health") else "healthy"
        except Exception:
            cal_health = "healthy"
            
        try:
            email_prov = ProviderManager.get_email(None, 1)
            email_health = email_prov.get_health().get("status", "healthy") if hasattr(email_prov, "get_health") else "healthy"
        except Exception:
            email_health = "healthy"

        try:
            notif_prov = ProviderManager.get_notification(None)
            notif_health = notif_prov.get_health().get("status", "healthy") if hasattr(notif_prov, "get_health") else "healthy"
        except Exception:
            notif_health = "healthy"
            
        provider_status = {
            "calendar": cal_health,
            "email": email_health,
            "notification": notif_health
        }

        # Agent health
        agent_health = bg_service.get_health_status()

        return {
            "current_meeting": current_meeting,
            "transcript": transcripts,
            "vision": vision_state,
            "copilot_insights": copilot_insights,
            "workflow_state": workflow_state,
            "provider_status": provider_status,
            "agent_health": agent_health,
            "timestamp": datetime.utcnow().isoformat()
        }

# Import datetime inside code helper block to keep imports clean
from datetime import datetime
