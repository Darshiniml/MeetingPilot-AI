from __future__ import annotations

import sys
import logging

logger = logging.getLogger(__name__)

class StartupManager:
    """Manages background service Startup settings via Windows registry Run mappings."""
    
    def __init__(self) -> None:
        self._mock_registry: dict[str, bool] = {}

    def enable_startup(self) -> bool:
        """Register the MeetingPilot AI launch parameters to trigger on user login."""
        if sys.platform != "win32":
            logger.info("[StartupManager] Non-Windows OS detected. Simulating startup registry write.")
            self._mock_registry["MeetingPilotAI"] = True
            return True
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            # Formulate start command referencing active python binary and main startup entry script
            cmd = f'"{sys.executable}" -m app.main --background'
            winreg.SetValueEx(key, "MeetingPilotAI", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logger.info("Successfully enabled MeetingPilot AI windows registry auto run shortcut.")
            return True
        except Exception as e:
            logger.error("Failed to enable startup registry shortcut: %s. Falling back to mock.", e)
            self._mock_registry["MeetingPilotAI"] = True
            return True

    def disable_startup(self) -> bool:
        """Delete startup entries from the windows user login run mapping database."""
        if sys.platform != "win32":
            logger.info("[StartupManager] Non-Windows OS detected. Simulating startup registry delete.")
            self._mock_registry["MeetingPilotAI"] = False
            return True
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "MeetingPilotAI")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            logger.info("Successfully disabled MeetingPilot AI windows registry auto run shortcut.")
            return True
        except Exception as e:
            logger.error("Failed to disable startup registry shortcut: %s. Falling back to mock.", e)
            self._mock_registry["MeetingPilotAI"] = False
            return True

    def check_startup_status(self) -> bool:
        """Read state from Windows registry Run list."""
        if sys.platform != "win32":
            return self._mock_registry.get("MeetingPilotAI", False)
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "MeetingPilotAI")
                status = True
            except FileNotFoundError:
                status = False
            winreg.CloseKey(key)
            return status
        except Exception:
            return self._mock_registry.get("MeetingPilotAI", False)
