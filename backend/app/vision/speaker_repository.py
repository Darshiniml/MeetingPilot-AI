"""In-memory storage for active speaker vision history."""

from collections import deque
from datetime import datetime
from threading import Lock

from app.vision.models import Participant


class SpeakerRepository:
    """Thread-safe circular buffer for recent vision frames."""

    def __init__(self, max_history: int = 1000) -> None:
        self._history: deque[tuple[datetime, tuple[Participant, ...]]] = deque(maxlen=max_history)
        self._lock = Lock()

    def add_frame(self, timestamp: datetime, participants: tuple[Participant, ...]) -> None:
        """Store the participants detected in one vision frame."""
        with self._lock:
            self._history.append((timestamp, participants))

    def get_frames_in_range(
        self, start_time: datetime, end_time: datetime
    ) -> list[tuple[datetime, tuple[Participant, ...]]]:
        """Retrieve all frames bounded inclusively by the given timestamps."""
        with self._lock:
            return [
                (ts, parts)
                for ts, parts in self._history
                if start_time <= ts <= end_time
            ]

    def clear(self) -> None:
        """Clear the history (e.g., when a meeting stops)."""
        with self._lock:
            self._history.clear()


_speaker_repository: SpeakerRepository | None = None
_repo_lock = Lock()


def get_speaker_repository() -> SpeakerRepository:
    """Return the singleton instance of the speaker repository."""
    global _speaker_repository
    with _repo_lock:
        if _speaker_repository is None:
            _speaker_repository = SpeakerRepository()
        return _speaker_repository
