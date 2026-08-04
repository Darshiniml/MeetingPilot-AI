"""WebSocket endpoint for live transcript streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import get_transcript_socket_manager


router = APIRouter(tags=["transcript-websocket"])


@router.websocket("/ws/transcript")
async def transcript_socket(websocket: WebSocket, token: str | None = None) -> None:
    """Accept a client and stream transcript chunks in real time."""
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

    manager = get_transcript_socket_manager()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
