from __future__ import annotations

import logging
from typing import Any
from app.background.meeting_detection.meeting_registry import MeetingPlatformProfile, MeetingPlatformRegistry

logger = logging.getLogger(__name__)

class MeetingClassifier:
    """Combines window titles, process names, browser URLs, and device activity signals into confidence metrics."""
    
    def __init__(self, platform_registry: MeetingPlatformRegistry) -> None:
        self.registry = platform_registry

    def classify_meeting(
        self,
        foreground_window: dict[str, Any] | None,
        browser_url: str | None,
        running_processes: list[str],
        mic_active: bool,
        speaker_active: bool = False
    ) -> tuple[MeetingPlatformProfile | None, float, list[str]]:
        """Calculate platform matching scores and return the highest confidence match."""
        if not foreground_window and not running_processes:
            return None, 0.0, []

        best_profile: MeetingPlatformProfile | None = None
        highest_confidence = 0.0
        best_signals = []

        window_title = foreground_window.get("title", "") if foreground_window else ""
        window_proc = foreground_window.get("process_name", "").lower() if foreground_window else ""

        # Evaluate each platform profile
        for profile in self.registry.get_profiles():
            confidence = 0.0
            signals = []
            
            # 1. Window title match
            window_matched = False
            if window_title:
                for pattern in profile.window_patterns:
                    if pattern.lower() in window_title.lower():
                        window_matched = True
                        break
            if window_matched:
                confidence += profile.weights.get("window", 0.3)
                signals.append("window_title")

            # 2. Browser url match
            url_matched = False
            if browser_url:
                for pattern in profile.url_patterns:
                    if pattern.lower() in browser_url.lower():
                        url_matched = True
                        break
            if url_matched:
                confidence += profile.weights.get("browser", 0.4)
                signals.append("browser_url")

            # 3. Process execution match
            proc_matched = False
            # Check if active foreground window is the app
            if window_proc and any(p.lower() in window_proc for p in profile.process_names):
                proc_matched = True
            # Or if client process is detected in running list
            elif any(p.lower() in [proc.lower() for proc in running_processes] for p in profile.process_names):
                proc_matched = True
                
            if proc_matched:
                confidence += profile.weights.get("process", 0.2)
                signals.append("running_process")

            # 4. Microphone active match
            # Microphone adds confidence only if there is already a window or process indication of a meeting
            if mic_active and (window_matched or proc_matched or url_matched):
                confidence += profile.weights.get("microphone", 0.1)
                signals.append("active_microphone")

            # 5. Speaker active match (bonus dynamic indicator)
            if speaker_active and (window_matched or proc_matched or url_matched):
                confidence += 0.05
                signals.append("active_speaker_output")

            # Normalize cap at 1.0
            confidence = min(1.0, confidence)

            if confidence > highest_confidence:
                highest_confidence = confidence
                best_profile = profile
                best_signals = signals

        # Ignore match if confidence is extremely low (noise)
        if highest_confidence < 0.15:
            return None, 0.0, []

        return best_profile, highest_confidence, best_signals
