"""Orchestrates live meeting state aggregation, analyzer coordination, and WS streaming."""

import time
import logging
from datetime import datetime, timezone
from typing import Any, MutableSet
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.copilot.copilot_models import LiveMeetingState, CopilotInsight
from app.copilot.live_analyzer import LiveAnalyzer
from app.copilot.insight_engine import InsightEngine

logger = logging.getLogger(__name__)


class CopilotSocketManager:
    """Track connected copilot clients and broadcast real-time meeting updates."""

    def __init__(self) -> None:
        self._connections: MutableSet[WebSocket] = set()
        self._event_loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new client connection."""
        await websocket.accept()
        self._connections.add(websocket)
        self._event_loop = asyncio.get_running_loop()
        await websocket.send_json({"type": "connected", "message": "Copilot stream connected"})

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client connection."""
        self._connections.discard(websocket)

    async def broadcast_copilot_update(self, meeting_id: int, update_data: dict[str, Any]) -> None:
        """Send copilot update payload to all active connections."""
        payload = {"type": "copilot_update", "meeting_id": meeting_id, **update_data}
        dead_connections: list[WebSocket] = []
        for conn in list(self._connections):
            try:
                await conn.send_json(payload)
            except Exception:
                dead_connections.append(conn)
        for conn in dead_connections:
            self._connections.discard(conn)

    def dispatch_copilot_update(self, meeting_id: int, update_data: dict[str, Any]) -> None:
        """Schedule a broadcast task onto the main event loop thread-safely."""
        if not self._connections or self._event_loop is None:
            return
        coroutine = self.broadcast_copilot_update(meeting_id=meeting_id, update_data=update_data)
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if current_loop is self._event_loop:
            current_loop.create_task(coroutine)
            return
        asyncio.run_coroutine_threadsafe(coroutine, self._event_loop)


_copilot_socket_manager = CopilotSocketManager()


def get_copilot_socket_manager() -> CopilotSocketManager:
    """Get the singleton Copilot WebSocket manager."""
    return _copilot_socket_manager


router = APIRouter(tags=["copilot-websocket"])


@router.websocket("/ws/copilot")
async def copilot_socket(websocket: WebSocket, token: str | None = None) -> None:
    """Exposes real-time copilot updates stream with security token checks."""
    if token is None:
        await websocket.close(code=1008)
        return

    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    manager = get_copilot_socket_manager()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


class LiveCopilotService:
    """Aggregates transcript segments, speaker events, tracks metrics, and broadcasts updates."""

    def __init__(self) -> None:
        self._states: dict[int, LiveMeetingState] = {}
        self.live_analyzer = LiveAnalyzer()
        self.insight_engine = InsightEngine()
        
        # Metrics trackers
        self.metrics = {
            "insights_generated": 0,
            "recommendations": 0,
            "decisions": 0,
            "risks": 0,
            "questions": 0,
            "commitments": 0,
            "average_latency_ms": 0.0,
            "processing_count": 0,
        }

    def handle_meeting_started(self, meeting_id: int, user_id: int) -> None:
        """Create and register a fresh meeting state container."""
        logger.info("LiveCopilotService initializing state for meeting=%d user=%d", meeting_id, user_id)
        self._states[meeting_id] = LiveMeetingState(
            meeting_id=meeting_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc)
        )

    def handle_meeting_stopped(self, meeting_id: int) -> None:
        """Archive and clean up memory structures for the stopped meeting."""
        logger.info("LiveCopilotService teardown state for meeting=%d", meeting_id)
        self._states.pop(meeting_id, None)

    def handle_transcript_saved(self, meeting_id: int, payload: dict[str, Any]) -> None:
        """Process incoming segment text, run detectors, compute metrics, and push updates."""
        state = self._states.get(meeting_id)
        if not state:
            # Lazy initialize if meeting start event was missed
            state = LiveMeetingState(
                meeting_id=meeting_id,
                user_id=payload.get("user_id") or 1,
                started_at=datetime.now(timezone.utc)
            )
            self._states[meeting_id] = state

        start_time = time.perf_counter()

        text = payload.get("text", "")
        speaker = payload.get("speaker_name") or "Unknown"

        # Record transcript chunk in history
        state.transcript_chunks.append(payload)

        # Update speaking duration
        duration = float(payload.get("end_seconds", 0) - payload.get("start_seconds", 0))
        if duration > 0:
            state.speaking_times[speaker] = state.speaking_times.get(speaker, 0.0) + duration

        # Ensure active speaker is recorded and present in participant lists
        state.active_speaker = speaker
        if speaker not in state.participants and speaker != "Unknown":
            state.participants.append(speaker)

        # 1. Run detectors to extract decisions, risks, deadlines, commitments, and questions
        new_insights = self.insight_engine.process_segment(state, text, speaker)
        state.insights.extend(new_insights)

        # Update metrics
        for insight in new_insights:
            self.metrics["insights_generated"] += 1
            typ = insight.insight_type
            if typ == "decision":
                self.metrics["decisions"] += 1
            elif typ == "risk":
                self.metrics["risks"] += 1
            elif typ == "deadline":
                self.metrics["recommendations"] += 1 # deadlines count as recommendations/coaching
            elif typ == "question":
                self.metrics["questions"] += 1
            elif typ == "commitment":
                self.metrics["commitments"] += 1

        # 2. Run analysis (speaking stats, dominant speaker, balance, and recommendation alerts)
        analysis_result = self.live_analyzer.analyze_meeting(state)
        
        # Increment recommendations metrics count
        self.metrics["recommendations"] += len(analysis_result.get("new_recommendations", []))

        # Compute latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.metrics["processing_count"] += 1
        curr_avg = self.metrics["average_latency_ms"]
        count = self.metrics["processing_count"]
        self.metrics["average_latency_ms"] = curr_avg + (latency_ms - curr_avg) / count

        # 3. Format and dispatch socket updates
        timeline = self.build_timeline(state)
        
        update_payload = {
            "insights": [ins.model_dump(mode="json") for ins in state.insights],
            "open_questions": state.open_questions,
            "resolved_questions": state.resolved_questions,
            "action_items": state.action_items,
            "engagement": analysis_result["engagement"],
            "timeline": timeline,
            "elapsed_minutes": analysis_result["elapsed_minutes"]
        }
        
        # Log latency
        logger.info(
            "Copilot processed segment: meeting_id=%d text_len=%d latency=%.2f ms total_insights=%d",
            meeting_id, len(text), latency_ms, len(state.insights)
        )

        get_copilot_socket_manager().dispatch_copilot_update(
            meeting_id=meeting_id,
            update_data=update_payload
        )

    def handle_speaker_changed(self, meeting_id: int, payload: dict[str, Any]) -> None:
        """Record speaker change and increment speaking ratios."""
        state = self._states.get(meeting_id)
        if not state:
            return
        new_speaker = payload.get("new_speaker")
        if new_speaker:
            state.active_speaker = new_speaker
            if new_speaker not in state.participants:
                state.participants.append(new_speaker)

    def handle_vision_updated(self, meeting_id: int, payload: dict[str, Any]) -> None:
        """Consume screen layout participant rosters."""
        state = self._states.get(meeting_id)
        if not state:
            return
        participants = payload.get("participants") or []
        for name in participants:
            if name not in state.participants and name != "Unknown":
                state.participants.append(name)

    def build_timeline(self, state: LiveMeetingState) -> list[dict[str, Any]]:
        """Synthesize chronological log coordinates of detected milestones."""
        sorted_insights = sorted(state.insights, key=lambda x: x.timestamp)
        timeline = []
        for insight in sorted_insights:
            time_str = insight.timestamp.astimezone(timezone.utc).strftime("%H:%M")
            timeline.append({
                "time": time_str,
                "type": insight.insight_type.upper(),
                "content": insight.content
            })
        return timeline

    def get_meeting_state(self, meeting_id: int) -> LiveMeetingState | None:
        """Fetch the active in-memory meeting state."""
        return self._states.get(meeting_id)

    def get_metrics(self) -> dict[str, Any]:
        """Fetch cumulative performance metrics."""
        return self.metrics


# Global singleton instance
_live_copilot_service = None


def get_live_copilot_service() -> LiveCopilotService:
    """Return the shared LiveCopilotService singleton."""
    global _live_copilot_service
    if _live_copilot_service is None:
        _live_copilot_service = LiveCopilotService()
    return _live_copilot_service
