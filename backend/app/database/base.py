"""Declarative base class shared by all SQLAlchemy ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Collect metadata for every MeetingPilot database table."""

