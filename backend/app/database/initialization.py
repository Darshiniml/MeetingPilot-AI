"""Database schema initialization for local application startup."""

from sqlalchemy import inspect, text

from app.database.base import Base
from app.database.connection import engine


def create_database_tables() -> None:
    """Import ORM mappings and create any tables absent from the database."""
    from app.models.action_item import ActionItem
    from app.models.meeting import Meeting
    from app.models.summary import Summary
    from app.models.transcript import Transcript

    _migrate_transcript_schema()
    Base.metadata.create_all(bind=engine)


def _migrate_transcript_schema() -> None:
    """Upgrade the early transcript table to the chunk-level Whisper schema."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("transcripts"):
            return
        column_names = {
            column["name"]
            for column in inspector.get_columns("transcripts")
        }
        if "chunk_index" in column_names:
            return
        if not {"sequence_number", "content"} <= column_names:
            raise RuntimeError("Unsupported transcripts table schema")

        connection.execute(text("ALTER TABLE transcripts RENAME TO transcripts_legacy"))
        Base.metadata.tables["transcripts"].create(connection, checkfirst=True)
        connection.execute(
            text(
                """
                INSERT INTO transcripts (
                    id, meeting_id, chunk_index, text, start_seconds,
                    end_seconds, language, confidence, created_at, updated_at
                )
                SELECT
                    id, meeting_id, sequence_number, content, 0.0,
                    0.0, 'unknown', NULL, created_at, updated_at
                FROM transcripts_legacy
                """
            )
        )
        connection.execute(text("DROP TABLE transcripts_legacy"))
