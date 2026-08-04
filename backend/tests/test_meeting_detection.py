import pytest
import time
from datetime import datetime, timezone
from app.background import BackgroundService, ServiceManager
from app.background.meeting_detection import MeetingDetectionModule, MeetingSession, MeetingPlatformProfile
from app.background.meeting_detection.meeting_events import MeetingDetectedEvent, MeetingLostEvent
from app.agent.events.event_types import EventType

def test_multi_signal_confidence_calculation():
    # Setup detector
    srv = BackgroundService.get_instance()
    detector = MeetingDetectionModule(srv.event_bus)
    
    # 1. Test Chrome + Google Meet url + Microphone Active
    window = {"title": "Chrome - meet.google.com/abc-defg-hij", "process_name": "chrome.exe", "handle": 100}
    detector.window_detector.set_simulated_window(window)
    detector.process_detector.set_simulated_processes(["chrome.exe"])
    detector.audio_detector.set_simulated_audio(microphone_active=True, speaker_active=False)
    
    # Evaluate signals
    url = detector.browser_detector.extract_meeting_url(window)
    assert url == "meet.google.com/abc-defg-hij"
    
    profile, conf, signals = detector.classifier.classify_meeting(
        window, url, ["chrome.exe"], mic_active=True, speaker_active=False
    )
    
    assert profile is not None
    assert profile.platform_name == "Google Meet"
    # window weight (0.3) + browser weight (0.4) + process weight (0.2) + mic weight (0.1) = 1.0
    assert conf == pytest.approx(1.0)
    assert "window_title" in signals
    assert "browser_url" in signals
    assert "running_process" in signals
    assert "active_microphone" in signals

def test_detection_profile_thresholds():
    srv = BackgroundService.get_instance()
    
    # Aggressive profile
    det_aggressive = MeetingDetectionModule(srv.event_bus, profile="Aggressive")
    assert det_aggressive.threshold == 0.25
    
    # Balanced profile
    det_balanced = MeetingDetectionModule(srv.event_bus, profile="Balanced")
    assert det_balanced.threshold == 0.5
    
    # Conservative profile
    det_conservative = MeetingDetectionModule(srv.event_bus, profile="Conservative")
    assert det_conservative.threshold == 0.8

def test_custom_platform_registration():
    srv = BackgroundService.get_instance()
    detector = MeetingDetectionModule(srv.event_bus)
    
    # Register custom platform
    custom = MeetingPlatformProfile(
        platform_name="CustomMeet",
        process_names=["custom_app.exe"],
        window_patterns=["customroom"],
        url_patterns=["custom.com/join"]
    )
    detector.platform_registry.register_profile(custom)
    
    window = {"title": "customroom link", "process_name": "custom_app.exe", "handle": 101}
    detector.window_detector.set_simulated_window(window)
    detector.process_detector.set_simulated_processes(["custom_app.exe"])
    detector.audio_detector.set_simulated_audio(microphone_active=True, speaker_active=False)
    
    url = detector.browser_detector.extract_meeting_url(window)
    profile, conf, signals = detector.classifier.classify_meeting(
        window, url, ["custom_app.exe"], mic_active=True, speaker_active=False
    )
    
    assert profile is not None
    assert profile.platform_name == "CustomMeet"
    assert conf > 0.5

def test_stability_timer_and_lifecycle():
    srv = BackgroundService.get_instance()
    
    # Configure detector with stability duration 0.1s and loss duration 0.1s for fast tests execution
    detector = MeetingDetectionModule(
        srv.event_bus,
        profile="Balanced",
        policy="Autonomous",
        stability_duration=0.1,
        loss_duration=0.1
    )
    
    # Track received EventBus messages
    received_types = []
    def on_event(event):
        received_types.append(event.event_type)
        
    srv.event_bus.subscribe(EventType.MEETING_DETECTED, on_event)
    srv.event_bus.subscribe(EventType.MEETING_STARTED, on_event)
    srv.event_bus.subscribe(EventType.MEETING_STOPPED, on_event)
    srv.event_bus.subscribe(EventType.MEETING_LOST, on_event)

    # 1. State is IDLE
    assert detector.current_state == "IDLE"
    
    # 2. Simulate active meeting signals
    window = {"title": "Zoom Meeting ID 123", "process_name": "zoom.exe", "handle": 202}
    detector.window_detector.set_simulated_window(window)
    detector.process_detector.set_simulated_processes(["zoom.exe"])
    detector.audio_detector.set_simulated_audio(microphone_active=True, speaker_active=False)
    
    # Evaluate first scan (not stable yet, state should still be IDLE)
    detector._evaluate_signals()
    assert detector.current_state == "IDLE"
    assert len(received_types) == 0
    
    # Wait for stability duration and scan again
    time.sleep(0.15)
    detector._evaluate_signals()
    
    # Under Autonomous policy, stable detection auto-starts monitoring!
    assert detector.current_state == "MONITORING"
    assert EventType.MEETING_DETECTED in received_types
    assert EventType.MEETING_STARTED in received_types
    
    # 3. Simulate meeting signal loss
    detector.window_detector.set_simulated_window(None)
    detector.process_detector.set_simulated_processes([])
    detector.audio_detector.set_simulated_audio(microphone_active=False, speaker_active=False)
    
    # Evaluate first lost scan (state should still be MONITORING)
    detector._evaluate_signals()
    assert detector.current_state == "MONITORING"
    
    # Wait for loss stability duration and scan again
    time.sleep(0.15)
    detector._evaluate_signals()
    
    # State transitions back to IDLE, meeting stop published
    assert detector.current_state == "IDLE"
    assert EventType.MEETING_STOPPED in received_types

def test_assisted_confirmation_policy():
    srv = BackgroundService.get_instance()
    
    # Configure detector with Assisted policy
    detector = MeetingDetectionModule(
        srv.event_bus,
        profile="Balanced",
        policy="Assisted",
        stability_duration=0.01,
        loss_duration=0.01
    )
    
    received_types = []
    def on_event(event):
        received_types.append(event.event_type)
        
    srv.event_bus.subscribe(EventType.MEETING_DETECTED, on_event)
    srv.event_bus.subscribe(EventType.MEETING_STARTED, on_event)
    srv.event_bus.subscribe(EventType.MEETING_LOST, on_event)
    
    # Simulate a medium-confidence meeting (window title only, no active mic/browser link)
    # Confidence weight: window (0.3) + process (0.2) = 0.5 (meets balanced threshold 0.5)
    window = {"title": "Microsoft Teams Room", "process_name": "teams.exe", "handle": 303}
    detector.window_detector.set_simulated_window(window)
    detector.process_detector.set_simulated_processes(["teams.exe"])
    detector.audio_detector.set_simulated_audio(microphone_active=False, speaker_active=False)
    
    # Evaluate scan
    detector._evaluate_signals()
    time.sleep(0.02)
    detector._evaluate_signals()
    
    # State should remain in WAITING_CONFIRMATION since confidence is 0.5 (medium, Assisted asks user)
    assert detector.current_state == "WAITING_CONFIRMATION"
    assert EventType.MEETING_DETECTED in received_types
    assert EventType.MEETING_STARTED not in received_types
    
    # User declines meeting monitoring
    detector.trigger_confirmation_response(approve=False)
    assert detector.current_state == "IDLE"
    assert EventType.MEETING_LOST in received_types
