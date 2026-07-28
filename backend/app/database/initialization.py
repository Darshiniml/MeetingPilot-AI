"""Database schema initialization for local application startup."""

from app.database.base import Base
from app.database.connection import engine


def create_database_tables() -> None:
    """Import ORM mappings and create any tables absent from the database."""
    from app.models.action_item import ActionItem
    from app.models.meeting import Meeting
    from app.models.summary import Summary
    from app.models.transcript import Transcript

    Base.metadata.create_all(bind=engine)
