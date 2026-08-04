from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

class RecordingPolicy:
    """Manages start policies: Manual, Assisted, Autonomous."""
    
    def __init__(self, mode: str = "Balanced") -> None:
        # Policy modes: Manual, Assisted, Autonomous
        self.mode = mode

    def should_auto_start(self, confidence: float, threshold: float) -> bool:
        """Determines if the meeting should automatically trigger recording based on the policy."""
        mode_lower = self.mode.lower()
        if mode_lower == "manual":
            return False
        elif mode_lower == "assisted":
            # Auto-start only for high-confidence detections (>0.75)
            return confidence >= 0.75
        else:
            # Autonomous mode
            return confidence >= threshold
