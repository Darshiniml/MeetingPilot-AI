from __future__ import annotations

import logging
import asyncio
from typing import Any
from app.providers.notification.local_notification import LocalNotificationProvider

logger = logging.getLogger(__name__)

class WebSocketNotificationProvider(LocalNotificationProvider):
    """Broadcasting notifier transmitting real time event payloads to active WebSocket sessions."""
    
    def send_notification(
        self,
        title: str,
        message: str,
        category: str = "general",
        severity: str = "INFO",
        workflow_id: str | None = None,
        meeting_id: int | None = None
    ) -> bool:
        # Write to SQLite database
        super().send_notification(title, message, category, severity, workflow_id, meeting_id)
        
        try:
            from app.websocket.manager import get_transcript_socket_manager
            manager = get_transcript_socket_manager()
            
            if not manager._connections or manager._event_loop is None:
                return True
                
            payload = {
                "type": "notification",
                "notification": {
                    "title": title,
                    "message": message,
                    "category": category,
                    "severity": severity,
                    "workflow_id": workflow_id,
                    "meeting_id": meeting_id
                }
            }
            
            async def do_broadcast():
                dead_connections = []
                for ws in list(manager._connections):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        dead_connections.append(ws)
                for ws in dead_connections:
                    manager._connections.discard(ws)

            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if current_loop is manager._event_loop:
                current_loop.create_task(do_broadcast())
            else:
                asyncio.run_coroutine_threadsafe(do_broadcast(), manager._event_loop)
                
            logger.info("Notification broadcasted via WebSockets: %s", title)
            return True
        except Exception as e:
            logger.error("Failed to broadcast alert over websockets connection manager: %s", e)
            self.error_info = str(e)
            return False

    def get_health(self) -> dict[str, Any]:
        h = super().get_health()
        h["capabilities"].append("websocket_broadcasting")
        return h
