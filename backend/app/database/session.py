"""SQLAlchemy session factory and FastAPI session dependency."""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import engine


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one database session per request and close it afterwards."""
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
