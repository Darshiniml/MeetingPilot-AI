"""Contract tests for the meeting lifecycle HTTP API."""

import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class MeetingApiTests(unittest.TestCase):
    """Ensure the existing frontend-facing meeting API remains stable."""

    def setUp(self) -> None:
        """Create an app client and reset shared in-memory state for each test."""
        self.client = TestClient(create_app())
        self.client.post("/meeting/stop")

    def test_system_endpoints(self) -> None:
        """Root and health endpoints retain their original JSON responses."""
        self.assertEqual(
            self.client.get("/").json(),
            {"message": "🚀 MeetingPilot AI Backend is Running!"},
        )
        self.assertEqual(self.client.get("/health").json(), {"status": "healthy"})

    def test_meeting_lifecycle(self) -> None:
        """Meeting status changes from stopped to running and back again."""
        self.assertEqual(self.client.get("/meeting/status").json(), {"running": False})
        self.assertEqual(
            self.client.post("/meeting/start").json(),
            {"message": "Meeting Started", "running": True},
        )
        self.assertEqual(self.client.get("/meeting/status").json(), {"running": True})
        self.assertEqual(
            self.client.post("/meeting/stop").json(),
            {"message": "Meeting Stopped", "running": False},
        )
