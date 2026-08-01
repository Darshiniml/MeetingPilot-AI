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
    from app.models.vector_embedding import VectorEmbedding

    _migrate_transcript_schema()
    _migrate_action_item_schema()
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
            if "segment_index" not in column_names:
                connection.execute(text("ALTER TABLE transcripts RENAME TO transcripts_legacy_v2"))
                Base.metadata.tables["transcripts"].create(connection, checkfirst=True)
                connection.execute(
                    text(
                        """
                        INSERT INTO transcripts (
                            id, meeting_id, chunk_index, segment_index, text, start_seconds,
                            end_seconds, language, confidence, speaker_id, speaker_name, speaker_confidence, created_at, updated_at
                        )
                        SELECT
                            id, meeting_id, chunk_index, 0, text, start_seconds,
                            end_seconds, language, confidence, NULL, NULL, NULL, created_at, updated_at
                        FROM transcripts_legacy_v2
                        """
                    )
                )
                connection.execute(text("DROP TABLE transcripts_legacy_v2"))
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


def _migrate_action_item_schema() -> None:
    """Add AI-extraction metadata to databases created before this milestone."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("action_items"):
            return
        column_names = {column["name"] for column in inspector.get_columns("action_items")}
        if "priority" not in column_names:
            connection.execute(text("ALTER TABLE action_items ADD COLUMN priority VARCHAR(32)"))
