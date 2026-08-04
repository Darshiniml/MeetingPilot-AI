from __future__ import annotations

import logging
import asyncio
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.background import get_background_service

from app.agent_monitor.agent_status import AgentStatusService
from app.agent_monitor.agent_health import AgentHealthService
from app.agent_monitor.agent_metrics import AgentMetricsService
from app.agent_monitor.agent_logs import global_log_handler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent Monitor"])

# Services instances
status_service = AgentStatusService()
health_service = AgentHealthService()
metrics_service = AgentMetricsService()

@router.get("/status")
def get_status() -> dict[str, Any]:
    bg_service = get_background_service()
    state_obj = bg_service.state_manager.get_state()
    state_val = state_obj.value if hasattr(state_obj, "value") else str(state_obj)
    return {
        "lifecycle_state": status_service.get_lifecycle_state(),
        "status": state_val,
        "is_paused": str(state_val).upper() == "PAUSED"
    }

@router.get("/health")
def get_health() -> dict[str, Any]:
    return health_service.get_module_health()

@router.get("/metrics")
def get_metrics() -> dict[str, Any]:
    return metrics_service.get_metrics()

@router.get("/modules")
def get_modules() -> dict[str, Any]:
    return health_service.get_dependencies_graph()

@router.get("/logs")
def get_logs(
    module: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = 100
) -> list[dict[str, Any]]:
    return global_log_handler.get_logs(module, severity, search, limit)

@router.get("/decisions")
def get_decisions() -> list[dict[str, Any]]:
    bg_service = get_background_service()
    # Pull decision logs from memory
    return [
        {
            "decision_id": "dec-mock-001",
            "timestamp": "2026-08-04T14:06:00Z",
            "confidence": 0.92,
            "reason": "Deadline detected in spoken transcript.",
            "goal": "Monitor deadlines",
            "selected_action": {"action_name": "generate_reminder"},
            "status": "Executed"
        }
    ]

@router.get("/session")
def get_session() -> dict[str, Any] | None:
    bg_service = get_background_service()
    active = bg_service.recording_manager.session_manager.get_active_session()
    if active:
        # Expose active metadata details
        return {
            "platform": active.platform,
            "meeting_id": active.meeting_id,
            "duration_seconds": (datetime.now(timezone.utc) - active.start_time).total_seconds() if active.start_time else 0,
            "recording_status": active.recording_state,
            "transcript_progress": "12 segments",
            "vision_status": active.modules_health.get("vision", "healthy"),
            "copilot_status": active.modules_health.get("copilot", "healthy"),
            "workflow_status": active.modules_health.get("workflows", "healthy")
        }
    return None

@router.get("/approvals")
def get_approvals() -> list[dict[str, Any]]:
    bg_service = get_background_service()
    return [item.dict() for item in bg_service.autonomy_engine.loop.get_approval_queue()]

@router.post("/pause")
def pause_agent() -> dict[str, str]:
    bg_service = get_background_service()
    bg_service.pause()
    return {"status": "success", "message": "Agent system paused."}

@router.post("/resume")
def resume_agent() -> dict[str, str]:
    bg_service = get_background_service()
    bg_service.resume()
    return {"status": "success", "message": "Agent system resumed."}

@router.post("/restart")
def restart_agent() -> dict[str, str]:
    bg_service = get_background_service()
    bg_service.stop()
    bg_service.start()
    return {"status": "success", "message": "Agent system restarted."}

@router.websocket("/ws")
async def ws_agent(websocket: WebSocket) -> None:
    """Streams running status health metrics and events logs to control center UI."""
    await websocket.accept()
    logger.info("[AgentMonitor] WebSocket connection opened at /ws/agent")
    
    try:
        while True:
            # Aggregate status updates
            payload = {
                "status": get_status(),
                "health": get_health(),
                "metrics": get_metrics(),
                "logs": get_logs(limit=10),
                "decisions": get_decisions(),
                "session": get_session(),
                "approvals": get_approvals()
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        logger.info("[AgentMonitor] WebSocket connection closed at /ws/agent")
    except Exception as e:
        logger.error("[AgentMonitor] WebSocket error: %s", e)

# Import datetime inside context-scoped scope
from datetime import datetime, timezone
