from __future__ import annotations

from threading import RLock

class AutonomyMetrics:
    """Thread-safe statistics counters aggregating AI agent decisions, approvals, and latency metrics."""
    
    def __init__(self) -> None:
        self.decisions_made = 0
        self.decisions_skipped = 0
        self.recommendations = 0
        self.automatic_executions = 0
        self.approval_requests = 0
        self.approvals_accepted = 0
        self.approvals_rejected = 0
        self.total_reasoning_latency_seconds = 0.0
        self.total_confidence = 0.0
        self.cycles_count = 0
        self._lock = RLock()

    def record_decision(self, is_skipped: bool, is_recommendation: bool, is_auto: bool, confidence: float, latency: float) -> None:
        with self._lock:
            self.cycles_count += 1
            self.total_reasoning_latency_seconds += latency
            self.total_confidence += confidence
            if is_skipped:
                self.decisions_skipped += 1
            else:
                self.decisions_made += 1
                
            if is_recommendation:
                self.recommendations += 1
            if is_auto:
                self.automatic_executions += 1

    def record_approval_request(self) -> None:
        with self._lock:
            self.approval_requests += 1

    def record_approval_response(self, approved: bool) -> None:
        with self._lock:
            if approved:
                self.approvals_accepted += 1
            else:
                self.approvals_rejected += 1

    def get_average_confidence(self) -> float:
        with self._lock:
            if self.decisions_made == 0:
                return 0.0
            return self.total_confidence / self.decisions_made

    def get_average_latency(self) -> float:
        with self._lock:
            if self.cycles_count == 0:
                return 0.0
            return self.total_reasoning_latency_seconds / self.cycles_count

    def get_approval_success_rate(self) -> float:
        with self._lock:
            total_approvals = self.approvals_accepted + self.approvals_rejected
            if total_approvals == 0:
                return 1.0
            return self.approvals_accepted / total_approvals

    def serialize(self) -> dict:
        with self._lock:
            return {
                "decisions_made": self.decisions_made,
                "decisions_skipped": self.decisions_skipped,
                "recommendations": self.recommendations,
                "automatic_executions": self.automatic_executions,
                "approval_requests": self.approval_requests,
                "approval_success_rate": self.get_approval_success_rate(),
                "average_confidence": self.get_average_confidence(),
                "average_reasoning_latency_seconds": self.get_average_latency()
            }
