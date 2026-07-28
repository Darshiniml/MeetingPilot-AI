"""Database engine configuration."""

from sqlalchemy import create_engine
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
