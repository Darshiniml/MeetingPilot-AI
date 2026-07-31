"""In-memory WebSocket manager for live transcript broadcasting."""

from __future__ import annotations

from collections.abc import MutableSet
import asyncio
from typing import Any

from fastapi import WebSocket


class TranscriptSocketManager:
    """Track connected transcript clients and broadcast new transcript chunks."""

    def __init__(self) -> None:
        self._connections: MutableSet[WebSocket] = set()
        self._event_loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket client."""
        await websocket.accept()
        self._connections.add(websocket)
        self._event_loop = asyncio.get_running_loop()
        await websocket.send_json({"type": "connected", "message": "Transcript stream connected"})

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket client."""
        self._connections.discard(websocket)

    async def broadcast_transcript(self, *, meeting_id: int, transcript: dict[str, Any]) -> None:
        """Send a transcript chunk to every connected client."""
        payload = {"type": "transcript", "meeting_id": meeting_id, "transcript": transcript}
        dead_connections: list[WebSocket] = []
        for websocket in list(self._connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                dead_connections.append(websocket)
        for websocket in dead_connections:
            self._connections.discard(websocket)

    def dispatch_transcript(self, *, meeting_id: int, transcript: dict[str, Any]) -> None:
        """Schedule a broadcast on the ASGI loop from either request or worker threads."""
        if not self._connections or self._event_loop is None:
            return
        coroutine = self.broadcast_transcript(meeting_id=meeting_id, transcript=transcript)
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if current_loop is self._event_loop:
            current_loop.create_task(coroutine)
            return
        asyncio.run_coroutine_threadsafe(coroutine, self._event_loop).result(timeout=5)


_transcript_socket_manager: TranscriptSocketManager | None = None


def get_transcript_socket_manager() -> TranscriptSocketManager:
    """Return the shared transcript socket manager singleton."""
    global _transcript_socket_manager
    if _transcript_socket_manager is None:
        _transcript_socket_manager = TranscriptSocketManager()
    return _transcript_socket_manager
