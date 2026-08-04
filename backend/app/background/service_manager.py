from __future__ import annotations

import logging
from app.background.background_service import get_background_service
from app.background.background_state import BackgroundState

logger = logging.getLogger(__name__)

class ServiceManager:
    """Programmatic manager managing singleton execution and automatic recoveries."""
    
    @staticmethod
    def start_service() -> bool:
        """Start the background service. Enforces that only one service can be active at a time."""
        service = get_background_service()
        state = service.state_manager.get_state()
        
        if state in (BackgroundState.STARTING, BackgroundState.RUNNING):
            logger.warning("[ServiceManager] Background service is already starting or running. Ignoring duplicate start request.")
            return False
            
        try:
            service.start()
            return True
        except Exception as e:
            logger.error("[ServiceManager] Failed to start background service: %s", e)
            service.state_manager.transition_to(BackgroundState.ERROR, error_details=str(e))
            return False

    @staticmethod
    def stop_service() -> bool:
        """Gracefully shutdown the running background service singleton."""
        service = get_background_service()
        state = service.state_manager.get_state()
        
        if state in (BackgroundState.STOPPED, BackgroundState.SHUTTING_DOWN):
            logger.warning("[ServiceManager] Background service is already stopped or shutting down.")
            return False
            
        try:
            service.stop()
            return True
        except Exception as e:
            logger.error("[ServiceManager] Error occurred during background service shutdown: %s", e)
            return False

    @staticmethod
    def restart_service() -> bool:
        """Performs a clean restart, resetting state metrics counters."""
        logger.info("[ServiceManager] Restart sequence triggered.")
        ServiceManager.stop_service()
        
        service = get_background_service()
        service.metrics.increment_restarts()
        
        return ServiceManager.start_service()
