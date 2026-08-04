from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.providers import ProviderManager, ProviderRegistry

router = APIRouter(prefix="/providers", tags=["providers"])

class SwitchProviderRequest(BaseModel):
    category: str = Field(..., description="The category of provider, e.g. 'calendar', 'email', 'notification', 'storage'")
    provider: str = Field(..., description="The provider name to activate, e.g. 'local', 'google', 'smtp', 'websocket'")

@router.get("")
def get_providers():
    """Retrieve currently active and supported provider options."""
    config = ProviderManager.load_config()
    supported = ProviderRegistry.list_supported()
    return {
        "active": config,
        "supported": supported
    }

@router.post("/switch")
def switch_provider(req: SwitchProviderRequest):
    """Switch active provider selection for a category persistently."""
    category = req.category.lower().strip()
    provider = req.provider.lower().strip()
    
    supported = ProviderRegistry.list_supported()
    if category not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported provider category: {category}")
        
    if provider not in supported[category]:
        raise HTTPException(status_code=400, detail=f"Unsupported provider option '{provider}' for category '{category}'")
        
    ProviderManager.set_active(category, provider)
    return {
        "success": True,
        "message": f"Successfully updated category '{category}' to provider '{provider}'",
        "active": ProviderManager.load_config()
    }

@router.get("/health")
def get_provider_health(db: Session = Depends(get_db)):
    """Retrieve dynamic health metrics summaries for all active providers."""
    # Instantiates active providers and queries health
    cal = ProviderManager.get_calendar(db, 1)
    email = ProviderManager.get_email(db, 1)
    notif = ProviderManager.get_notification(db)
    storage = ProviderManager.get_storage()
    
    # Extract underlying active helper from FallbackProxy if resolved
    def extract_health(proxy):
        if proxy._active_provider and hasattr(proxy._active_provider, "get_health"):
            try:
                return proxy._active_provider.get_health()
            except Exception as e:
                return {"status": "offline", "error_info": str(e)}
        return {"status": "unknown"}

    return {
        "calendar": extract_health(cal),
        "email": extract_health(email),
        "notification": extract_health(notif),
        "storage": extract_health(storage)
    }

@router.get("/capabilities")
def get_provider_capabilities():
    """List exposed capability sets per registered provider class."""
    supported = ProviderRegistry.list_supported()
    capabilities_map = {}
    
    # Query static capabilities by temporarily instantiating defaults
    for cat, names in supported.items():
        capabilities_map[cat] = {}
        for name in names:
            factory = ProviderRegistry.get_factory(cat, name)
            if factory:
                try:
                    prov = factory(None, 1)
                    if hasattr(prov, "get_health"):
                        capabilities_map[cat][name] = prov.get_health().get("capabilities", [])
                except Exception:
                    capabilities_map[cat][name] = []
                    
    return capabilities_map

@router.get("/notifications")
def list_notifications(is_read: bool | None = None, category: str | None = None, db: Session = Depends(get_db)):
    """Expose Notification Center query list from SQLite database."""
    notif = ProviderManager.get_notification(db)
    return notif.list_notifications(is_read=is_read, category=category)

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Mark a registered notification as read in the SQLite alerts log."""
    notif = ProviderManager.get_notification(db)
    notif.mark_as_read(notification_id)
    return {"success": True}
