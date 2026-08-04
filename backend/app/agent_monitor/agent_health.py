from __future__ import annotations

import logging
from typing import Any
from app.background import get_background_service

logger = logging.getLogger(__name__)

class AgentHealthService:
    """Aggregates active health reports and dependencies status grids."""
    
    def __init__(self) -> None:
        pass

    def get_module_health(self) -> dict[str, str]:
        """Resolves module health states for all active systems."""
        bg_service = get_background_service()
        
        # Audio service, Whisper, Vision health
        active_session = bg_service.recording_manager.session_manager.get_active_session()
        modules_health = active_session.modules_health if active_session else {}

        # Autonomy Engine health
        autonomy_health = "Running" if bg_service.autonomy_engine.loop._running else "Idle"

        # Meeting Detector health
        md_state = bg_service.meeting_detector.current_state if hasattr(bg_service.meeting_detector, "current_state") else "IDLE"
        if hasattr(md_state, "value"):
            md_state = md_state.value
        md_health = "Running" if str(md_state).upper() != "IDLE" else "Idle"

        state_obj = bg_service.state_manager.get_state()
        state_val = state_obj.value if hasattr(state_obj, "value") else str(state_obj)

        return {
            "Background Service": "Running" if str(state_val).upper() == "RUNNING" else "Idle",
            "Meeting Detector": md_health,
            "Recording Manager": "Running" if active_session else "Idle",
            "Audio Service": modules_health.get("audio", "Idle"),
            "Whisper": modules_health.get("whisper", "Idle"),
            "Vision": modules_health.get("vision", "Idle"),
            "Copilot": modules_health.get("copilot", "Idle"),
            "Workflow Engine": modules_health.get("workflows", "Idle"),
            "Supervisor Agent": "Running",
            "Autonomy Engine": autonomy_health,
            "Memory": modules_health.get("memory", "Running"),
            "Provider Manager": "Running",
            "A2A": "Running",
            "MCP": "Running"
        }

    def get_dependencies_graph(self) -> dict[str, Any]:
        """Expose dependency relationships mapping with live running statuses."""
        health = self.get_module_health()
        return {
            "name": "Background Agent",
            "status": health["Background Service"],
            "children": [
                {
                    "name": "Meeting Detection",
                    "status": health["Meeting Detector"],
                    "children": [
                        {
                            "name": "Recording Pipeline",
                            "status": health["Recording Manager"],
                            "children": [
                                {"name": "Whisper", "status": health["Whisper"]},
                                {"name": "Vision", "status": health["Vision"]},
                                {"name": "Copilot", "status": health["Copilot"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Autonomy Engine",
                    "status": health["Autonomy Engine"],
                    "children": [
                        {"name": "Workflow Engine", "status": health["Workflow Engine"]},
                        {"name": "Memory", "status": health["Memory"]},
                        {"name": "Providers", "status": health["Provider Manager"]}
                    ]
                }
            ]
        }
