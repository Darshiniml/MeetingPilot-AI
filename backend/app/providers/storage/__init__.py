from __future__ import annotations

from typing import Protocol, Any

class StorageProvider(Protocol):
    """Protocol interface defining requirements for Storage connection provider plugins."""
    
    def get_session_factory(self) -> Any:
        """Retrieve SQLAlchemy sessionmaker instance for active storage database."""
        ...

    def get_health(self) -> dict[str, Any]:
        """Retrieve dynamic health metrics details for this provider instance."""
        ...
