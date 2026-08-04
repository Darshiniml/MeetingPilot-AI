"""Meeting domain state and SQLAlchemy persistence model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlAlchemyEnum, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.summary import Summary
    from app.models.transcript import Transcript
    from app.models.user import User


def utc_now() -> datetime:
    """Return the current UTC timestamp as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class MeetingStatus(str, Enum):
    """Allowed lifecycle states for a persisted meeting."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class Meeting(Base):
    """Persisted meeting lifecycle record."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[MeetingStatus] = mapped_column(
        SqlAlchemyEnum(
            MeetingStatus,
            native_enum=False,
            create_constraint=True,
            name="meeting_status",
        ),
        nullable=False,
        default=MeetingStatus.CREATED,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_meet_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invitation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invitation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Transcript.chunk_index",
    )
    summary: Mapped["Summary | None"] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="meetings",
    )

@dataclass(slots=True)
class MeetingState:
    """The current state of a single active meeting session."""

    running: bool = False
    meeting_id: int | None = None
