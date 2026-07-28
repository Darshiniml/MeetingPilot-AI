"""WebSocket streaming tests for live transcript delivery."""

import asyncio
import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.websocket.manager import get_transcript_socket_manager


class TranscriptWebsocketTests(unittest.TestCase):
    """Ensure transcript updates are pushed immediately over WebSocket."""

    def test_transcript_websocket_broadcasts_chunks(self) -> None:
        """Clients receive transcript events without polling."""
        with TestClient(create_app()) as client:
            with client.websocket_connect("/ws/transcript") as websocket:
                connected_message = websocket.receive_json()
                self.assertEqual(connected_message["type"], "connected")

                manager = get_transcript_socket_manager()

                async def emit() -> None:
                    await manager.broadcast_transcript(
                        meeting_id=7,
                        transcript={
                            "id": 11,
                            "meeting_id": 7,
                            "chunk_index": 1,
                            "text": "Live transcript chunk",
                            "start_seconds": 0.0,
                            "end_seconds": 1.5,
                            "language": "en",
                            "confidence": 0.97,
                        },
                    )

                asyncio.run(emit())

                received_message = websocket.receive_json()
                self.assertEqual(received_message["type"], "transcript")
                self.assertEqual(received_message["meeting_id"], 7)
                self.assertEqual(received_message["transcript"]["text"], "Live transcript chunk")
