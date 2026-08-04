from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.provider_models import ProviderConfig

logger = logging.getLogger(__name__)

# Pre-defined priorities (can be dynamically overridden in db)
DEFAULT_PRIORITIES = {
    "calendar": ["local", "ics", "google", "outlook", "caldav"],
    "email": ["local", "smtp", "mailtrap", "gmail", "sendgrid", "resend"],
    "notification": ["local", "desktop", "websocket"],
    "storage": ["sqlite", "postgres"]
}

class ProviderRegistry:
    """Central registry mapping category names to constructor factories."""
    
    _registry: dict[str, dict[str, Any]] = {
        "calendar": {},
        "email": {},
        "notification": {},
        "storage": {}
    }

    @classmethod
    def register(cls, category: str, name: str, factory: Any) -> None:
        category = category.lower().strip()
        name = name.lower().strip()
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][name] = factory
        logger.info("Provider registered: category=%s name=%s", category, name)

    @classmethod
    def get_factory(cls, category: str, name: str) -> Any:
        return cls._registry.get(category, {}).get(name)

    @classmethod
    def list_supported(cls) -> dict[str, list[str]]:
        return {cat: list(provs.keys()) for cat, provs in cls._registry.items()}

# Automatically register all standard providers
from app.providers.calendar.local_calendar import LocalCalendarProvider
from app.providers.calendar.ics_calendar import ICSCalendarProvider
from app.providers.calendar.google_calendar import GoogleCalendarProviderWrapper
from app.providers.calendar.stubs import OutlookCalendarProvider, CalDAVProvider

ProviderRegistry.register("calendar", "local", lambda session, user_id: LocalCalendarProvider(session))
ProviderRegistry.register("calendar", "ics", lambda session, user_id: ICSCalendarProvider())
ProviderRegistry.register("calendar", "google", lambda session, user_id: GoogleCalendarProviderWrapper(session, user_id))
ProviderRegistry.register("calendar", "outlook", lambda session, user_id: OutlookCalendarProvider())
ProviderRegistry.register("calendar", "caldav", lambda session, user_id: CalDAVProvider())

from app.providers.email.local_email import LocalEmailProvider
from app.providers.email.smtp_email import SMTPProvider
from app.providers.email.stubs import GmailProviderWrapper, MailtrapProvider, SendGridProvider, ResendProvider

ProviderRegistry.register("email", "local", lambda session, user_id: LocalEmailProvider(session))
ProviderRegistry.register("email", "smtp", lambda session, user_id: SMTPProvider())
ProviderRegistry.register("email", "gmail", lambda session, user_id: GmailProviderWrapper(session, user_id))
ProviderRegistry.register("email", "mailtrap", lambda session, user_id: MailtrapProvider())
ProviderRegistry.register("email", "sendgrid", lambda session, user_id: SendGridProvider())
ProviderRegistry.register("email", "resend", lambda session, user_id: ResendProvider())

from app.providers.notification.local_notification import LocalNotificationProvider
from app.providers.notification.desktop_notification import DesktopNotificationProvider
from app.providers.notification.websocket_notification import WebSocketNotificationProvider

ProviderRegistry.register("notification", "local", lambda session, user_id: LocalNotificationProvider(session))
ProviderRegistry.register("notification", "desktop", lambda session, user_id: DesktopNotificationProvider(session))
ProviderRegistry.register("notification", "websocket", lambda session, user_id: WebSocketNotificationProvider(session))

from app.providers.storage.sqlite_storage import SQLiteProvider
from app.providers.storage.postgres_storage import PostgresProvider

ProviderRegistry.register("storage", "sqlite", lambda session, user_id: SQLiteProvider())
ProviderRegistry.register("storage", "postgres", lambda session, user_id: PostgresProvider())


class FallbackProxy:
    """Proxy container that automatically falls back to next priority provider if primary fails."""
    
    def __init__(self, category: str, session: Session | None, user_id: int) -> None:
        self.category = category
        self.session = session
        self.user_id = user_id
        self._active_provider = None
        self._active_name = None
        self._resolve_active()

    def _resolve_active(self) -> None:
        config = ProviderManager.load_config(self.session)
        active_name = config.get(self.category)
        
        # Pull priorities list and ensure active_name is checked first
        priorities = list(DEFAULT_PRIORITIES.get(self.category, []))
        if active_name in priorities:
            priorities.remove(active_name)
        priorities = [active_name] + priorities
            
        for name in priorities:
            factory = ProviderRegistry.get_factory(self.category, name)
            if factory:
                try:
                    prov = factory(self.session, self.user_id)
                    # Check health
                    if hasattr(prov, "get_health"):
                        health = prov.get_health()
                        if health["status"] == "offline":
                            logger.warning("Provider '%s' is offline, trying next priority fallback.", name)
                            continue
                    self._active_provider = prov
                    self._active_name = name
                    return
                except Exception as e:
                    logger.error("Failed to instantiate provider '%s': %s", name, e)
                    
        # Fallback to local
        factory = ProviderRegistry.get_factory(self.category, "local")
        if factory:
            self._active_provider = factory(self.session, self.user_id)
            self._active_name = "local"

    def __getattr__(self, name: str) -> Any:
        if self._active_provider is None:
            raise RuntimeError(f"No active provider resolved for category '{self.category}'")
            
        attr = getattr(self._active_provider, name)
        if not callable(attr):
            return attr
            
        def wrapper(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except Exception as e:
                logger.error("Active provider '%s' failed during call to '%s': %s. Executing automatic fallback.", self._active_name, name, e)
                # Attempt to switch to local fallback provider
                factory = ProviderRegistry.get_factory(self.category, "local")
                if factory and self._active_name != "local":
                    fallback_prov = factory(self.session, self.user_id)
                    self._active_provider = fallback_prov
                    self._active_name = "local"
                    ProviderManager.set_active(self.category, "local", self.session)
                    # Retry operation
                    fallback_attr = getattr(fallback_prov, name)
                    return fallback_attr(*args, **kwargs)
                raise e
        return wrapper


class ProviderManager:
    """Centralized manager coordinating configuration state and active provider instances."""
    
    @staticmethod
    def load_config(session: Session | None = None) -> dict[str, str]:
        """Load current configuration mapping from SQLite table."""
        config = {
            "calendar": "local",
            "email": "local",
            "notification": "local",
            "storage": "sqlite"
        }
        
        db = session if session is not None else SessionLocal()
        try:
            rows = db.query(ProviderConfig).all()
            for r in rows:
                config[r.key] = r.value
        except Exception as e:
            logger.error("Failed to load configs from SQLite table: %s", e)
        finally:
            if session is None:
                db.close()
            
        return config

    @staticmethod
    def set_active(category: str, name: str, session: Session | None = None) -> None:
        """Update active setting for category persistently in SQLite database."""
        db = session if session is not None else SessionLocal()
        try:
            cfg = db.query(ProviderConfig).filter_by(key=category).first()
            if cfg:
                cfg.value = name
            else:
                cfg = ProviderConfig(key=category, value=name)
                db.add(cfg)
            db.commit()
            logger.info("Persisted provider settings switch in database: category=%s name=%s", category, name)
        except Exception as e:
            logger.error("Failed to persist config in SQLite: %s", e)
        finally:
            if session is None:
                db.close()

    @classmethod
    def get_calendar(cls, session: Session | None, user_id: int) -> Any:
        return FallbackProxy("calendar", session, user_id)

    @classmethod
    def get_email(cls, session: Session | None, user_id: int) -> Any:
        return FallbackProxy("email", session, user_id)

    @classmethod
    def get_notification(cls, session: Session | None = None) -> Any:
        # User ID dummy for notification interface compatibility
        return FallbackProxy("notification", session, 1)

    @classmethod
    def get_storage(cls) -> Any:
        return FallbackProxy("storage", None, 1)


# Maintain backward compatibility getters routing through ProviderManager
def get_calendar_provider(session: Session, user_id: int) -> Any:
    return ProviderManager.get_calendar(session, user_id)

def get_email_provider(session: Session, user_id: int) -> Any:
    return ProviderManager.get_email(session, user_id)

def get_notification_provider() -> Any:
    return ProviderManager.get_notification()

def get_storage_provider() -> Any:
    return ProviderManager.get_storage()

def set_active_provider(category: str, provider_name: str) -> None:
    ProviderManager.set_active(category, provider_name)

def load_providers_config() -> dict[str, str]:
    return ProviderManager.load_config()
