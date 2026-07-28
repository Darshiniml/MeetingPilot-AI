"""Database schema initialization for local application startup."""

from app.database.base import Base
from app.database.connection import engine


def create_database_tables() -> None:
    """Import ORM mappings and create any tables absent from the database."""
    from app.models.meeting import Meeting

    Base.metadata.create_all(bind=engine)
