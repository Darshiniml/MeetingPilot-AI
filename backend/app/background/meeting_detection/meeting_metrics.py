from __future__ import annotations

from threading import RLock

class MeetingMetrics:
    """Telemetry counters aggregating meeting detection accuracy, platforms, and latencies."""
    
    def __init__(self) -> None:
        self.meetings_detected = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.total_latency_seconds = 0.0
        self.total_confidence = 0.0
        self.detections_count = 0
        self.meeting_durations: list[float] = []
        self.platform_distribution: dict[str, int] = {}
        self._lock = RLock()

    def record_detection(self, platform: str, confidence: float, latency: float) -> None:
        with self._lock:
            self.meetings_detected += 1
            self.detections_count += 1
            self.total_confidence += confidence
            self.total_latency_seconds += latency
            self.platform_distribution[platform] = self.platform_distribution.get(platform, 0) + 1

    def record_false_positive(self) -> None:
        with self._lock:
            self.false_positives += 1

    def record_false_negative(self) -> None:
        with self._lock:
            self.false_negatives += 1

    def record_meeting_duration(self, duration_seconds: float) -> None:
        with self._lock:
            self.meeting_durations.append(duration_seconds)

    def get_average_confidence(self) -> float:
        with self._lock:
            if self.detections_count == 0:
                return 0.0
            return self.total_confidence / self.detections_count

    def get_average_latency(self) -> float:
        with self._lock:
            if self.detections_count == 0:
                return 0.0
            return self.total_latency_seconds / self.detections_count

    def serialize(self) -> dict:
        with self._lock:
            avg_dur = sum(self.meeting_durations) / len(self.meeting_durations) if self.meeting_durations else 0.0
            return {
                "meetings_detected": self.meetings_detected,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
                "average_latency_seconds": self.get_average_latency(),
                "average_confidence": self.get_average_confidence(),
                "average_duration_seconds": avg_dur,
                "platform_distribution": dict(self.platform_distribution)
            }
