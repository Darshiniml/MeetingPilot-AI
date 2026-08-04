"""Database schema initialization for local application startup."""

import logging
import os

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

def create_database_tables() -> None:
    """Run Alembic migrations and create schema tables."""
    logger.info("Running database migrations...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    command.upgrade(alembic_cfg, "head")
    
    # Create any missing additive tables (e.g. providers configurations, local calendars)
    from app.database.connection import engine
    from app.database.base import Base
    import app.models.provider_models
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database migrations completed successfully.")
