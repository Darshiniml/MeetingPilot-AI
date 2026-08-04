"""Database schema initialization for local application startup."""

import logging
import os

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

def create_database_tables() -> None:
    """Run Alembic migrations to update database schema."""
    logger.info("Running database migrations...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed successfully.")
