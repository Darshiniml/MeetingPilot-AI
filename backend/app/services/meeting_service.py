"""Meeting lifecycle business logic."""

from threading import RLock

from app.models.meeting import MeetingState


class MeetingService:
    """Manage the current meeting lifecycle behind a replaceable service boundary.

    State remains in memory for the current product stage. The lock makes each
    transition safe when FastAPI serves requests concurrently. A future
    repository, event publisher, transcription worker, or database can be
    introduced here without changing route handlers.
    """

    def __init__(self) -> None:
        self._state = MeetingState()
        self._lock = RLock()

    def get_status(self) -> MeetingState:
        """Return a snapshot of the current meeting state."""
        with self._lock:
            return MeetingState(running=self._state.running)

    def start_meeting(self) -> MeetingState:
        """Start the meeting and return the resulting state."""
        with self._lock:
            self._state.running = True
            return MeetingState(running=self._state.running)

    def stop_meeting(self) -> MeetingState:
        """Stop the meeting and return the resulting state."""
        with self._lock:
            self._state.running = False
            return MeetingState(running=self._state.running)


_meeting_service = MeetingService()


def get_meeting_service() -> MeetingService:
    """Provide the application service for FastAPI dependency injection."""
    return _meeting_service
