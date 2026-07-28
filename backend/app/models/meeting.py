"""Meeting domain state and SQLAlchemy persistence model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlAlchemyEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.summary import Summary
    from app.models.transcript import Transcript


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
    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Transcript.sequence_number",
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

@dataclass(slots=True)
class MeetingState:
    """The current state of a single active meeting session."""

    running: bool = False
