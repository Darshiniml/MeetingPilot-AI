"""SQLAlchemy model for timestamped meeting transcript chunks."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.meeting import utc_now

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class Transcript(Base):
    """A sequential source chunk captured from one meeting."""

    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "chunk_index",
            "segment_index",
            name="uq_transcripts_meeting_chunk_segment",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speaker_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speaker_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    meeting: Mapped["Meeting"] = relationship(back_populates="transcripts")
