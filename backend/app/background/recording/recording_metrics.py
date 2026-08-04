from __future__ import annotations

from threading import RLock

class RecordingMetrics:
    """Thread-safe statistics tracking recording pipeline performance."""
    
    def __init__(self) -> None:
        self.meetings_recorded = 0
        self.dropped_sessions = 0
        self.chunks_processed = 0
        self.transcript_segments = 0
        self.copilot_insights = 0
        self.workflow_executions = 0
        self.recovery_attempts = 0
        self.failures_count = 0
        self.total_pipeline_latency = 0.0
        self.recording_durations: list[float] = []
        self._lock = RLock()

    def record_session_started(self) -> None:
        with self._lock:
            self.meetings_recorded += 1

    def record_dropped_session(self) -> None:
        with self._lock:
            self.dropped_sessions += 1

    def record_chunk_processed(self) -> None:
        with self._lock:
            self.chunks_processed += 1

    def record_transcript_segment(self) -> None:
        with self._lock:
            self.transcript_segments += 1

    def record_insight_generated(self) -> None:
        with self._lock:
            self.copilot_insights += 1

    def record_workflow_execution(self) -> None:
        with self._lock:
            self.workflow_executions += 1

    def record_recovery_attempt(self) -> None:
        with self._lock:
            self.recovery_attempts += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failures_count += 1

    def record_latency(self, latency_seconds: float) -> None:
        with self._lock:
            self.total_pipeline_latency += latency_seconds

    def record_duration(self, duration_seconds: float) -> None:
        with self._lock:
            self.recording_durations.append(duration_seconds)

    def get_success_rate(self) -> float:
        with self._lock:
            total_runs = self.meetings_recorded + self.dropped_sessions
            if total_runs == 0:
                return 1.0
            return (self.meetings_recorded - self.failures_count) / self.meetings_recorded if self.meetings_recorded > 0 else 0.0

    def serialize(self) -> dict:
        with self._lock:
            avg_dur = sum(self.recording_durations) / len(self.recording_durations) if self.recording_durations else 0.0
            return {
                "meetings_recorded": self.meetings_recorded,
                "dropped_sessions": self.dropped_sessions,
                "audio_chunks_processed": self.chunks_processed,
                "transcript_segments": self.transcript_segments,
                "copilot_insights_generated": self.copilot_insights,
                "workflow_executions": self.workflow_executions,
                "recovery_attempts": self.recovery_attempts,
                "failures": self.failures_count,
                "success_rate": self.get_success_rate(),
                "average_duration_seconds": avg_dur
            }
