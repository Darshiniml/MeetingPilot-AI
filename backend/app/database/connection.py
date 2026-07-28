"""Database engine configuration."""

from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.config.settings import get_settings


def create_database_engine() -> Engine:
    """Create the configured SQLAlchemy engine for the running application."""
    settings = get_settings()
    connect_args = (
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = create_database_engine()


def _enable_sqlite_foreign_keys(
    dbapi_connection: Any,
    _connection_record: Any,
) -> None:
    """Enable SQLite foreign-key enforcement for every application connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if engine.url.get_backend_name() == "sqlite":
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
