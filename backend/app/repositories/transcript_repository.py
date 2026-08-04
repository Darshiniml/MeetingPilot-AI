"""SQLAlchemy persistence operations for transcript chunks."""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.transcript import Transcript


class TranscriptRepository:
    """Persist and retrieve transcript chunks through an injected session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_transcript(self, *, meeting_id: int, chunk_index: int, segment_index: int, text: str, start_seconds: float, end_seconds: float, language: str, confidence: float | None, speaker_id: str | None, speaker_name: str | None, speaker_confidence: float | None) -> Transcript:
        """Create and persist one Whisper transcription segment."""
        transcript = Transcript(meeting_id=meeting_id, chunk_index=chunk_index, segment_index=segment_index, text=text, start_seconds=start_seconds, end_seconds=end_seconds, language=language, confidence=confidence, speaker_id=speaker_id, speaker_name=speaker_name, speaker_confidence=speaker_confidence)
        self._session.add(transcript)
        res = self._commit_and_refresh(transcript)
        import logging
        from sqlalchemy import func
        count = self._session.query(func.count(Transcript.id)).scalar()
        print(f"SELECT COUNT(*) FROM transcripts; -> {count}", flush=True)
        print(f"Current transcript count: {count}", flush=True)
        logging.getLogger(__name__).info(f"SELECT COUNT(*) FROM transcripts; -> {count}")
        return res

    def list_transcripts_for_meeting(self, meeting_id: int) -> Sequence[Transcript]:
        """Return a meeting's chunks in chronological order."""
        statement: Select[tuple[Transcript]] = select(Transcript).where(Transcript.meeting_id == meeting_id).order_by(Transcript.chunk_index.asc())
        return self._session.execute(statement).scalars().all()

    def get_transcript(self, transcript_id: int) -> Transcript | None:
        """Return a transcript by ID, or None when absent."""
        statement: Select[tuple[Transcript]] = select(Transcript).where(Transcript.id == transcript_id)
        return self._session.execute(statement).scalars().first()

    def delete_transcript(self, transcript: Transcript) -> None:
        """Permanently remove one transcript chunk."""
        self._session.delete(transcript)
        self._commit()

    def _commit_and_refresh(self, transcript: Transcript) -> Transcript:
        self._commit()
        self._session.refresh(transcript)
        return transcript

    def _commit(self) -> None:
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise
