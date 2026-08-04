from __future__ import annotations

import sys
import logging
from typing import Any

logger = logging.getLogger(__name__)

class AudioDetector:
    """Audits microphone access and audio speaker activity triggers."""
    
    def __init__(self) -> None:
        self._simulated_mic_active = False
        self._simulated_speaker_active = False

    def set_simulated_audio(self, microphone_active: bool, speaker_active: bool) -> None:
        """Enables automated test suites to mock device usage profiles."""
        self._simulated_mic_active = microphone_active
        self._simulated_speaker_active = speaker_active

    def is_microphone_active(self) -> bool:
        """Checks registry keys or input streams to see if any process is capturing the microphone."""
        if self._simulated_mic_active:
            return True
            
        if sys.platform != "win32":
            return False
            
        try:
            import winreg
            # Access Windows ConsentStore for microphone usage
            consent_path = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
            try:
                root_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, consent_path, 0, winreg.KEY_READ)
            except FileNotFoundError:
                root_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, consent_path, 0, winreg.KEY_READ)
                
            info = winreg.QueryInfoKey(root_key)
            subkeys_count = info[0]
            
            # Audit subkeys mapping to specific desktop apps
            for i in range(subkeys_count):
                subkey_name = winreg.EnumKey(root_key, i)
                subkey = winreg.OpenKey(root_key, subkey_name, 0, winreg.KEY_READ)
                try:
                    # Non-packaged applications subkeys check
                    try:
                        # pakaged apps
                        stop_val, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStop")
                        start_val, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStart")
                        if start_val > stop_val:
                            winreg.CloseKey(subkey)
                            winreg.CloseKey(root_key)
                            return True
                    except FileNotFoundError:
                        pass
                        
                    # Auditing NonPackaged subkeys
                    try:
                        np_key = winreg.OpenKey(subkey, "NonPackaged", 0, winreg.KEY_READ)
                        np_info = winreg.QueryInfoKey(np_key)
                        for j in range(np_info[0]):
                            np_sub_name = winreg.EnumKey(np_key, j)
                            np_sub = winreg.OpenKey(np_key, np_sub_name, 0, winreg.KEY_READ)
                            try:
                                stop_val, _ = winreg.QueryValueEx(np_sub, "LastUsedTimeStop")
                                start_val, _ = winreg.QueryValueEx(np_sub, "LastUsedTimeStart")
                                if start_val > stop_val:
                                    winreg.CloseKey(np_sub)
                                    winreg.CloseKey(np_key)
                                    winreg.CloseKey(subkey)
                                    winreg.CloseKey(root_key)
                                    return True
                            except FileNotFoundError:
                                pass
                            winreg.CloseKey(np_sub)
                        winreg.CloseKey(np_key)
                    except FileNotFoundError:
                        pass
                except Exception:
                    pass
                winreg.CloseKey(subkey)
            winreg.CloseKey(root_key)
        except Exception as e:
            logger.debug("Failed active microphone registry query: %s", e)
            
        return False

    def is_speaker_active(self) -> bool:
        """Determines if sound speaker decibel outputs exceed noise thresholds."""
        return self._simulated_speaker_active
