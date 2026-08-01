"""Temporal smoothing and transition tracking for active speaker detection."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SpeakerTracker:
    """Applies temporal smoothing to speaking states to avoid flicker and ignore brief flashes."""

    def __init__(
        self,
        rise_time: float = 0.25,
        decay_time: float = 1.2,
        active_threshold: float = 0.5,
    ) -> None:
        """Initialize the speaker tracker.

        Args:
            rise_time: Time in seconds of continuous speaking required to activate.
            decay_time: Time in seconds of silence required to deactivate.
            active_threshold: Score threshold in [0.0, 1.0] to consider active.
        """
        self._rise_time = rise_time
        self._decay_time = decay_time
        self._active_threshold = active_threshold

        # Dict mapping participant_id -> dict of tracker state
        self._states: dict[str, dict] = {}

    def update(
        self,
        participant_id: str,
        is_speaking_instant: bool,
        confidence: float,
        timestamp: datetime,
    ) -> tuple[bool, float]:
        """Update a participant's speaker status with new visual evidence.

        Returns:
            (is_active: bool, smoothed_confidence: float)
        """
        if participant_id not in self._states:
            self._states[participant_id] = {
                "score": 0.0,
                "last_timestamp": timestamp,
                "confidence": 0.0,
            }

        state = self._states[participant_id]
        dt = (timestamp - state["last_timestamp"]).total_seconds()
        state["last_timestamp"] = timestamp

        if dt < 0:
            dt = 0.0

        score = state["score"]
        if is_speaking_instant:
            # Increase speaker score (rise)
            step = (dt / self._rise_time) if self._rise_time > 0 else 1.0
            score = min(1.0, score + step)
            # Smooth confidence as a running average
            state["confidence"] = state["confidence"] + 0.3 * (confidence - state["confidence"])
        else:
            # Decrease speaker score (decay)
            step = (dt / self._decay_time) if self._decay_time > 0 else 1.0
            score = max(0.0, score - step)
            # Decay confidence
            state["confidence"] = max(0.0, state["confidence"] - 0.2 * dt)

        state["score"] = score
        is_active = score >= self._active_threshold

        return is_active, state["confidence"]

    def update_inactive_missing(self, participant_id: str, timestamp: datetime) -> None:
        """Decay the active speaker score of a participant not seen in the current frame."""
        if participant_id in self._states:
            state = self._states[participant_id]
            dt = (timestamp - state["last_timestamp"]).total_seconds()
            if dt > 0:
                state["last_timestamp"] = timestamp
                step = (dt / self._decay_time) if self._decay_time > 0 else 1.0
                state["score"] = max(0.0, state["score"] - step)
                state["confidence"] = max(0.0, state["confidence"] - 0.2 * dt)

    def prune(self, max_idle_seconds: float = 30.0, current_time: datetime = None) -> None:
        """Prune track states for participants that haven't been updated for a while."""
        if current_time is None:
            current_time = datetime.now()

        prune_keys = [
            key
            for key, state in self._states.items()
            if (current_time - state["last_timestamp"]).total_seconds() > max_idle_seconds
        ]
        for key in prune_keys:
            del self._states[key]
