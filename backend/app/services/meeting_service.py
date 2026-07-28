"""Meeting lifecycle business logic."""

from threading import RLock

from app.models.meeting import Meeting, MeetingState, MeetingStatus, utc_now
from app.repositories.meeting_repository import MeetingRepository


class MultipleRunningMeetingsError(RuntimeError):
    """Raised when persisted data violates the one-active-meeting invariant."""


class MeetingService:
    """Coordinate meeting lifecycle rules through the MeetingRepository."""

    _lifecycle_lock = RLock()

    def __init__(self, meeting_repository: MeetingRepository) -> None:
        """Initialize the service with its sole persistence collaborator."""
        self._meeting_repository = meeting_repository

    def get_status(self) -> MeetingState:
        """Return whether exactly one meeting is currently running."""
        return MeetingState(running=self._get_single_running_meeting() is not None)

    def start_meeting(self) -> MeetingState:
        """Start a meeting unless an existing meeting is already running."""
        with self._lifecycle_lock:
            if self._get_single_running_meeting() is not None:
                return MeetingState(running=True)

            self._meeting_repository.create_meeting(
                title="Untitled Meeting",
                status=MeetingStatus.RUNNING,
                started_at=utc_now(),
            )
            return MeetingState(running=True)

    def stop_meeting(self) -> MeetingState:
        """Complete the active meeting, or remain stopped when none exists."""
        with self._lifecycle_lock:
            running_meeting = self._get_single_running_meeting()
            if running_meeting is None:
                return MeetingState(running=False)

            running_meeting.status = MeetingStatus.COMPLETED
            running_meeting.ended_at = utc_now()
            self._meeting_repository.update_meeting(running_meeting)
            return MeetingState(running=False)

    def _get_single_running_meeting(self) -> Meeting | None:
        """Return one running meeting or raise when persisted state is invalid."""
        running_meetings = self._meeting_repository.list_running_meetings(limit=2)
        if len(running_meetings) > 1:
            raise MultipleRunningMeetingsError(
                "Multiple meetings are marked as RUNNING."
            )
        return running_meetings[0] if running_meetings else None
