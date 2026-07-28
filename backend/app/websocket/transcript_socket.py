"""WebSocket endpoint for live transcript streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import get_transcript_socket_manager


router = APIRouter(tags=["transcript-websocket"])


@router.websocket("/ws/transcript")
async def transcript_socket(websocket: WebSocket) -> None:
    """Accept a client and stream transcript chunks in real time."""
    manager = get_transcript_socket_manager()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
