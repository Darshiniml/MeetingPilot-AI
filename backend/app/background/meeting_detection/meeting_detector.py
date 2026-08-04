from __future__ import annotations

import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from app.agent.events.event_bus import EventBus
from app.background.meeting_detection.window_detector import WindowDetector
from app.background.meeting_detection.browser_detector import BrowserDetector
from app.background.meeting_detection.process_detector import ProcessDetector
from app.background.meeting_detection.audio_detector import AudioDetector
from app.background.meeting_detection.meeting_registry import MeetingRegistry, MeetingPlatformRegistry, MeetingSession
from app.background.meeting_detection.meeting_classifier import MeetingClassifier
from app.background.meeting_detection.meeting_metrics import MeetingMetrics
from app.background.meeting_detection.meeting_events import MeetingDetectedEvent, MeetingLostEvent
from app.agent.events.event_models import MeetingStartedEvent, MeetingStoppedEvent

logger = logging.getLogger(__name__)

class MeetingDetectionModule:
    """Pluggable background module orchestrating meeting classifications, lifecycle state machine transitions, and stability timers."""
    
    def __init__(
        self,
        event_bus: EventBus,
        profile: str = "Balanced",  # Conservative, Balanced, Aggressive
        policy: str = "Balanced",   # Manual, Assisted, Autonomous
        stability_duration: float = 3.0,
        loss_duration: float = 5.0
    ) -> None:
        self.event_bus = event_bus
        self.profile = profile
        self.policy = policy
        
        # Detection Thresholds based on profiles
        self.threshold = 0.5
        if profile.lower() == "conservative":
            self.threshold = 0.8
        elif profile.lower() == "aggressive":
            self.threshold = 0.25
            
        self.stability_duration = stability_duration
        self.loss_duration = loss_duration
        
        # Infrastructure detectors
        self.window_detector = WindowDetector()
        self.browser_detector = BrowserDetector()
        self.process_detector = ProcessDetector()
        self.audio_detector = AudioDetector()
        
        self.platform_registry = MeetingPlatformRegistry()
        self.classifier = MeetingClassifier(self.platform_registry)
        self.registry = MeetingRegistry()
        self.metrics = MeetingMetrics()
        
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        
        # State machine tracking
        self.current_state = "IDLE"  # IDLE, DETECTED, WAITING_CONFIRMATION, MONITORING, ENDED
        self._stable_detection_since: float | None = None
        self._stable_loss_since: float | None = None
        
        # Current active classification candidate
        self._candidate_platform: str | None = None
        self._active_session: MeetingSession | None = None

    def start(self) -> None:
        """Start the continuous meeting scan loop thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._scan_loop, name="MeetingDetectionLoop", daemon=True)
            self._thread.start()
            logger.info("Meeting Detection Engine started (Profile: %s, Threshold: %s).", self.profile, self.threshold)

    def stop(self) -> None:
        """Gracefully stop meeting scan loops."""
        with self._lock:
            self._running = False
            self._thread = None
            logger.info("Meeting Detection Engine stopped.")

    def trigger_confirmation_response(self, approve: bool) -> None:
        """Invoked by System Tray clicks or UI dialog selections to approve/reject detection prompts."""
        with self._lock:
            if self.current_state != "WAITING_CONFIRMATION" or not self._active_session:
                logger.warning("No meeting is currently waiting for confirmation approval.")
                return
                
            if approve:
                logger.info("[Detection Module] User approved meeting monitoring: %s", self._active_session.title)
                self.current_state = "MONITORING"
                self.registry.update_session_status(self._active_session.meeting_id, "MONITORING")
                
                # Publish MeetingStarted Event via EventBus
                start_evt = MeetingStartedEvent(
                    user_id=1,
                    meeting_id=None,
                    payload=self._build_event_payload()
                )
                self.event_bus.publish(start_evt)
            else:
                logger.info("[Detection Module] User declined meeting monitoring. Flagging as false positive.")
                self.metrics.record_false_positive()
                self.registry.update_session_status(self._active_session.meeting_id, "LOST")
                
                # Publish MeetingLost Event via EventBus
                lost_evt = MeetingLostEvent(
                    user_id=1,
                    payload=self._build_event_payload()
                )
                self.event_bus.publish(lost_evt)
                
                self._cleanup_session_state()

    def _scan_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self._evaluate_signals()
            except Exception as e:
                logger.error("Error evaluating meeting detection signals: %s", e)
            time.sleep(1.0)

    def _evaluate_signals(self) -> None:
        with self._lock:
            # Query active signals
            window = self.window_detector.get_foreground_window()
            url = self.browser_detector.extract_meeting_url(window) if window else None
            
            # Formulate list of target process names
            target_procs = set()
            for p in self.platform_registry.get_profiles():
                target_procs.update([name.lower() for name in p.process_names])
            processes = self.process_detector.get_active_meeting_processes(target_procs)
            
            mic = self.audio_detector.is_microphone_active()
            speaker = self.audio_detector.is_speaker_active()

            # Classify signals
            best_platform, confidence, signals = self.classifier.classify_meeting(
                window, url, processes, mic, speaker
            )

            now_time = time.perf_counter()

            # Lifecycle State Machine Processing
            if best_platform and confidence >= self.threshold:
                # We have a candidate meeting detected above the configured profile threshold
                self._stable_loss_since = None
                
                if self.current_state in ("IDLE", "ENDED"):
                    # Check stability timer
                    if self._candidate_platform != best_platform.platform_name:
                        self._candidate_platform = best_platform.platform_name
                        self._stable_detection_since = now_time
                    elif self._stable_detection_since is not None:
                        elapsed = now_time - self._stable_detection_since
                        if elapsed >= self.stability_duration:
                            # Detection is stable! Create session
                            self._initialize_meeting_session(best_platform, confidence, signals, window, processes)
                
                elif self.current_state in ("DETECTED", "WAITING_CONFIRMATION", "MONITORING"):
                    # Update active session metrics
                    if self._active_session:
                        self._active_session.confidence = confidence
                        self._active_session.signals_used = signals

            else:
                # No active meeting candidate detected above threshold
                self._stable_detection_since = None
                self._candidate_platform = None
                
                if self.current_state in ("DETECTED", "WAITING_CONFIRMATION", "MONITORING"):
                    if self._stable_loss_since is None:
                        self._stable_loss_since = now_time
                    else:
                        elapsed = now_time - self._stable_loss_since
                        if elapsed >= self.loss_duration:
                            self._terminate_meeting_session()

    def _initialize_meeting_session(self, platform: Any, confidence: float, signals: list[str], window: dict | None, processes: list[str]) -> None:
        title = window.get("title", f"Active {platform.platform_name}") if window else f"Active {platform.platform_name}"
        proc_name = window.get("process_name", processes[0] if processes else "") if window else (processes[0] if processes else "")
        
        session = MeetingSession(
            platform=platform.platform_name,
            window_handle=window.get("handle") if window else None,
            application=proc_name,
            title=title,
            confidence=confidence,
            signals_used=signals
        )
        
        self._active_session = session
        self.registry.add_session(session)
        
        logger.info("[Detection Module] Stable meeting detected: %s (Confidence: %s)", session.title, confidence)
        self.metrics.record_detection(platform.platform_name, confidence, self.stability_duration)
        
        # Publish MeetingDetected Event
        self.current_state = "DETECTED"
        self.event_bus.publish(MeetingDetectedEvent(
            user_id=1,
            payload=self._build_event_payload()
        ))

        # Check confirmation policy mode
        policy_mode = self.policy.lower()
        if policy_mode == "manual":
            self.current_state = "WAITING_CONFIRMATION"
            self.registry.update_session_status(session.meeting_id, "WAITING_CONFIRMATION")
        elif policy_mode == "assisted":
            if confidence > 0.75:
                # High confidence bypasses confirmation
                self._auto_start_monitoring()
            else:
                self.current_state = "WAITING_CONFIRMATION"
                self.registry.update_session_status(session.meeting_id, "WAITING_CONFIRMATION")
        else:
            # Autonomous mode
            self._auto_start_monitoring()

    def _auto_start_monitoring(self) -> None:
        self.current_state = "MONITORING"
        self.registry.update_session_status(self._active_session.meeting_id, "MONITORING")
        
        # Publish MeetingStarted Event
        start_evt = MeetingStartedEvent(
            user_id=1,
            meeting_id=None,
            payload=self._build_event_payload()
        )
        self.event_bus.publish(start_evt)
        logger.info("[Detection Module] Autonomous monitoring auto-started for session: %s", self._active_session.title)

    def _terminate_meeting_session(self) -> None:
        if not self._active_session:
            return
            
        logger.info("[Detection Module] Stable meeting loss confirmed: %s", self._active_session.title)
        
        # Record durations metrics
        duration = (datetime.now(timezone.utc) - self._active_session.start_time).total_seconds()
        self.metrics.record_meeting_duration(duration)

        old_state = self.current_state
        self.current_state = "ENDED"
        self.registry.update_session_status(self._active_session.meeting_id, "ENDED")
        
        # Publish MeetingEnded / MeetingLost events
        if old_state == "MONITORING":
            end_evt = MeetingStoppedEvent(
                user_id=1,
                meeting_id=None,
                payload=self._build_event_payload()
            )
            self.event_bus.publish(end_evt)
        else:
            # WAITING_CONFIRMATION or DETECTED status loss is considered a lost meeting
            lost_evt = MeetingLostEvent(
                user_id=1,
                payload=self._build_event_payload()
            )
            self.event_bus.publish(lost_evt)
            
        self._cleanup_session_state()

    def _cleanup_session_state(self) -> None:
        self.current_state = "IDLE"
        self._active_session = None
        self._candidate_platform = None
        self._stable_detection_since = None
        self._stable_loss_since = None

    def _build_event_payload(self) -> dict[str, Any]:
        if not self._active_session:
            return {}
        return {
            "meeting_id": self._active_session.meeting_id,
            "platform": self._active_session.platform,
            "confidence": self._active_session.confidence,
            "signals": self._active_session.signals_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "window_title": self._active_session.title,
            "process_name": self._active_session.application,
            "detection_profile": self.profile
        }
