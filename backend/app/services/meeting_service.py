"""Meeting lifecycle business logic."""

import logging
from collections.abc import Callable
from datetime import datetime
from threading import RLock

from app.audio.audio_service import AudioService
from app.audio.buffer import AudioChunk
from app.audio.devices import AudioSource
from app.models.meeting import Meeting, MeetingState, MeetingStatus, utc_now
from app.repositories.meeting_repository import MeetingRepository
from app.services.summary_service import SummaryService
from app.transcription.whisper_service import WhisperService


logger = logging.getLogger(__name__)


class MultipleRunningMeetingsError(RuntimeError):
    """Raised when persisted data violates the one-active-meeting invariant."""


class MeetingService:
    """Coordinate meeting lifecycle rules through the MeetingRepository."""

    _lifecycle_lock = RLock()

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        *,
        audio_service: AudioService,
        whisper_service: WhisperService,
        chunk_processor_factory: Callable[..., Callable[[AudioChunk], None]],
        summary_service: SummaryService,
    ) -> None:
        """Initialize the service with its sole persistence collaborator."""
        self._meeting_repository = meeting_repository
        self._audio_service = audio_service
        self._whisper_service = whisper_service
        self._chunk_processor_factory = chunk_processor_factory
        self._summary_service = summary_service

    def get_status(self) -> MeetingState:
        """Return whether exactly one meeting is currently running."""
        meeting = self._get_single_running_meeting()
        return MeetingState(running=meeting is not None, meeting_id=meeting.id if meeting else None)

    def start_meeting(self) -> MeetingState:
        """Start a meeting unless an existing meeting is already running."""
        with self._lifecycle_lock:
            if self._get_single_running_meeting() is not None:
                running_meeting = self._get_single_running_meeting()
                return MeetingState(running=True, meeting_id=running_meeting.id if running_meeting else None)

            meeting_started_at = utc_now()
            meeting = self._meeting_repository.create_meeting(
                title="Untitled Meeting",
                status=MeetingStatus.RUNNING,
                started_at=meeting_started_at,
            )
            self._audio_service.set_chunk_handler(
                self._chunk_processor_factory(
                    meeting_id=meeting.id,
                    meeting_started_at=meeting_started_at,
                    whisper_service=self._whisper_service,
                )
            )
            try:
                self._audio_service.start_recording(AudioSource.MICROPHONE)
            except Exception:
                self._audio_service.set_chunk_handler(None)
                meeting.status = MeetingStatus.COMPLETED
                meeting.ended_at = utc_now()
                self._meeting_repository.update_meeting(meeting)
                raise
            logger.info("Meeting started", extra={"meeting_id": meeting.id})
            return MeetingState(running=True, meeting_id=meeting.id)

    def stop_meeting(self) -> MeetingState:
        """Complete the active meeting, or remain stopped when none exists."""
        with self._lifecycle_lock:
            running_meeting = self._get_single_running_meeting()
            if running_meeting is None:
                return MeetingState(running=False)

            self._audio_service.stop_recording()
            self._audio_service.set_chunk_handler(None)
            running_meeting.status = MeetingStatus.COMPLETED
            running_meeting.ended_at = utc_now()
            self._meeting_repository.update_meeting(running_meeting)
            try:
                self._summary_service.generate_for_meeting(running_meeting.id)
            except Exception:
                logger.exception(
                    "Meeting stopped but summary generation failed",
                    extra={"meeting_id": running_meeting.id},
                )
            logger.info("Meeting stopped", extra={"meeting_id": running_meeting.id})
            return MeetingState(running=False, meeting_id=running_meeting.id)

    def get_summary(self, meeting_id: int):
        """Return a completed meeting's generated summary, if available."""
        return self._summary_service.get_for_meeting(meeting_id)

    def _get_single_running_meeting(self) -> Meeting | None:
        """Return one running meeting or raise when persisted state is invalid."""
        running_meetings = self._meeting_repository.list_running_meetings(limit=2)
        if len(running_meetings) > 1:
            raise MultipleRunningMeetingsError(
                "Multiple meetings are marked as RUNNING."
            )
        return running_meetings[0] if running_meetings else None
