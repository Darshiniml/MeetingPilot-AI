from __future__ import annotations

import sys
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ProcessDetector:
    """Scans running system process names to match dedicated meeting clients."""
    
    def __init__(self) -> None:
        self._simulated_processes: list[str] = []

    def set_simulated_processes(self, processes: list[str]) -> None:
        """Enables automated test suites to mock running system processes."""
        self._simulated_processes = processes

    def get_active_meeting_processes(self, platform_processes: set[str]) -> list[str]:
        """Scan running tasks for process name matches."""
        if self._simulated_processes:
            return [p for p in self._simulated_processes if p.lower() in platform_processes]
            
        if sys.platform != "win32":
            # CI environment stub
            return []
            
        try:
            import psutil
            active = []
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                    if name and name.lower() in platform_processes:
                        active.append(name.lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return active
        except Exception as e:
            logger.debug("Failed system process scan: %s. Returning mock fallback.", e)
            return []
            
    def is_process_running(self, process_name: str) -> bool:
        """Checks if a single process name is running."""
        name_lower = process_name.lower()
        if self._simulated_processes:
            return name_lower in [p.lower() for p in self._simulated_processes]
            
        if sys.platform != "win32":
            return False
            
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                    if name and name.lower() == name_lower:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return False
