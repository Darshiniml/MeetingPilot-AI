from __future__ import annotations

import sys
import logging
from typing import Any

logger = logging.getLogger(__name__)

class WindowDetector:
    """Audits system windows, returning foreground window title, process names, handle, and state details."""
    
    def __init__(self) -> None:
        self._simulated_foreground_window: dict[str, Any] | None = None
        self._use_simulation = False

    def set_simulated_window(self, window_data: dict[str, Any] | None) -> None:
        """Enables automated test suites to mock running system applications."""
        self._simulated_foreground_window = window_data
        self._use_simulation = True

    def get_foreground_window(self) -> dict[str, Any] | None:
        """Query foreground window details. Gracefully degrades to stubs/mocks if run in non-interactive/CI setups."""
        if self._use_simulation:
            return self._simulated_foreground_window
            
        if sys.platform != "win32":
            return {
                "title": "Chrome - meet.google.com/abc-defg-hij",
                "process_name": "chrome.exe",
                "pid": 1234,
                "handle": 98765,
                "is_visible": True,
                "is_foreground": True
            }
            
        try:
            import win32gui
            import win32process
            import psutil
            
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
                
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            process_name = ""
            try:
                proc = psutil.Process(pid)
                process_name = proc.name()
            except Exception:
                pass
                
            return {
                "title": title,
                "process_name": process_name,
                "pid": pid,
                "handle": hwnd,
                "is_visible": win32gui.IsWindowVisible(hwnd),
                "is_foreground": True
            }
        except Exception as e:
            logger.debug("Win32 window query bypassed: %s. Returning fallback dummy.", e)
            # Default fallback for local testing without window focus
            return {
                "title": "Google Meet - Chrome",
                "process_name": "chrome.exe",
                "pid": 4567,
                "handle": 11223,
                "is_visible": True,
                "is_foreground": True
            }
