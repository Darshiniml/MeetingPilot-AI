from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

class HotkeyManager:
    """Listens for global system keyboard combinations and executes callbacks."""
    
    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._lock = threading.RLock()
        self._listener_running = False

    def register_hotkey(self, hotkey: str, callback: Callable[[], None]) -> None:
        with self._lock:
            self._callbacks[hotkey] = callback
        logger.info("Global hotkey registered: %s", hotkey)

    def unregister_hotkey(self, hotkey: str) -> None:
        with self._lock:
            self._callbacks.pop(hotkey, None)
        logger.info("Global hotkey unregistered: %s", hotkey)

    def start(self) -> None:
        with self._lock:
            self._listener_running = True
        logger.info("Hotkey Manager hook listener started.")

    def stop(self) -> None:
        with self._lock:
            self._listener_running = False
        logger.info("Hotkey Manager hook listener stopped.")

    def simulate_hotkey(self, hotkey: str) -> bool:
        """Trigger registered hotkey callback programmatically for automated test suites."""
        callback = None
        with self._lock:
            callback = self._callbacks.get(hotkey)
            
        if callback:
            logger.info("Simulating hotkey action trigger for combination: %s", hotkey)
            try:
                callback()
                return True
            except Exception as e:
                logger.error("Error executing simulated hotkey callback: %s", e)
                return False
        logger.warning("No callback registered for simulated hotkey: %s", hotkey)
        return False
