from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class PostgresProvider:
    """Stub storage connection representing future enterprise PostgreSQL clustering."""
    
    def get_session_factory(self) -> Any:
        from app.database.session import SessionLocal
        logger.info("[PostgreSQL Provider Wrapper] Simulating connection pooling via sqlite fallback.")
        return SessionLocal

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 12,
            "version": "1.0.0",
            "capabilities": ["connection_pooling"],
            "last_sync": None,
            "error_info": None
        }
