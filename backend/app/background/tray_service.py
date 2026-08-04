from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

class TrayService:
    """System tray icon service coordinating task manager options and state updates."""
    
    def __init__(self, service_orchestrator: Any) -> None:
        self.service = service_orchestrator
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._simulated_menu_state: dict[str, bool] = {
            "Open Dashboard": True,
            "Pause Agent": True,
            "Resume Agent": False,
            "Start Recording": True,
            "Stop Recording": False,
            "Settings": True,
            "Exit": True
        }

    def start(self) -> None:
        """Start the system tray icon loop inside a separate thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._tray_loop, name="SystemTrayLoop", daemon=True)
            self._thread.start()
            logger.info("System Tray service started.")

    def stop(self) -> None:
        """Cleanly close the system tray icon."""
        with self._lock:
            self._running = False
            self._thread = None
            logger.info("System Tray service stopped.")

    def update_menu_state(self, is_paused: bool, is_recording: bool) -> None:
        """Sync internal UI toggle values to match orchestrator state changes."""
        with self._lock:
            self._simulated_menu_state["Pause Agent"] = not is_paused
            self._simulated_menu_state["Resume Agent"] = is_paused
            self._simulated_menu_state["Start Recording"] = not is_recording
            self._simulated_menu_state["Stop Recording"] = is_recording
        logger.debug("System Tray menu state updated: is_paused=%s is_recording=%s", is_paused, is_recording)

    def trigger_menu_action(self, action_name: str) -> bool:
        """Simulate system tray menu clicks dynamically inside test suites."""
        with self._lock:
            if action_name not in self._simulated_menu_state:
                logger.warning("Simulated menu action '%s' not supported.", action_name)
                return False
                
            if not self._simulated_menu_state[action_name]:
                logger.warning("Simulated menu action '%s' is currently disabled.", action_name)
                return False
                
        logger.info("Simulating click on system tray item: %s", action_name)
        try:
            if action_name == "Open Dashboard":
                # Simulated action
                pass
            elif action_name == "Pause Agent":
                self.service.pause()
            elif action_name == "Resume Agent":
                self.service.resume()
            elif action_name == "Start Recording":
                self.service.start_recording()
            elif action_name == "Stop Recording":
                self.service.stop_recording()
            elif action_name == "Exit":
                self.service.stop()
            return True
        except Exception as e:
            logger.error("Error executing simulated system tray item click: %s", e)
            return False

    def _tray_loop(self) -> None:
        """Daemon system tray loop (simulated headless loop)."""
        # Inside production build on Windows, we'd load pystray and call Icon.run().
        # To avoid blocking CI/Linux/Tests pipelines, we run this thread mock.
        while True:
            with self._lock:
                if not self._running:
                    break
            time.sleep(1.0)
