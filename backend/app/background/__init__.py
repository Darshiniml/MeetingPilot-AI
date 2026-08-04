from __future__ import annotations

# Import background_events to run dynamic enum expansion immediately
from app.background import background_events
from app.background.background_state import BackgroundState
from app.background.background_service import BackgroundService, get_background_service
from app.background.service_manager import ServiceManager
