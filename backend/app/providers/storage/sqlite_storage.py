from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class SQLiteProvider:
    """Production sqlite storage engine loading SessionLocal configurations."""
    
    def get_session_factory(self) -> Any:
        from app.database.session import SessionLocal
        return SessionLocal

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 1,
            "version": "1.0.0",
            "capabilities": ["SQLAlchemy", "sqlite_raw"],
            "last_sync": None,
            "error_info": None
        }
