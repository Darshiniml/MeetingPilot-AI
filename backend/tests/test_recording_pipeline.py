import pytest
import time
from unittest.mock import MagicMock, patch
from app.background import BackgroundService
from app.background.recording import RecordingManager, PipelineSession
from app.agent.events.event_types import EventType

class MockMeetingState:
    def __init__(self, running=True, meeting_id=42):
        self.running = running
        self.meeting_id = meeting_id

@pytest.fixture
def mock_meeting_service():
    service = MagicMock()
    service.start_meeting.return_value = MockMeetingState(running=True, meeting_id=99)
    service.stop_meeting.return_value = MockMeetingState(running=False, meeting_id=99)
    service._get_single_running_meeting.return_value = None
    return service

@pytest.fixture
def clean_recording_manager():
    srv = BackgroundService.get_instance()
    # Reset singleton mapping if already created to ensure clean tests runs
    RecordingManager._instance = None
    manager = RecordingManager.get_instance(srv.event_bus)
    manager.session_manager._active_session = None
    manager.session_manager._previous_sessions.clear()
    manager.metrics.__init__()
    return manager

def test_automatic_recording_start_stop(clean_recording_manager, mock_meeting_service):
    manager = clean_recording_manager
    srv = BackgroundService.get_instance()
    
    # Track EventBus notifications
    received_events = []
    def on_event(event):
        received_events.append(event.event_type)
        
    srv.event_bus.subscribe(EventType.SESSION_CREATED, on_event)
    srv.event_bus.subscribe(EventType.PIPELINE_STARTED, on_event)
    srv.event_bus.subscribe(EventType.RECORDING_STARTED, on_event)
    srv.event_bus.subscribe(EventType.RECORDING_STOPPED, on_event)
    srv.event_bus.subscribe(EventType.PIPELINE_COMPLETED, on_event)
    srv.event_bus.subscribe(EventType.SESSION_CLOSED, on_event)
    
    # Stub get_background_meeting_service context manager to return our mock service
    with patch("app.background.recording.pipeline_controller.get_background_meeting_service") as mock_ctx:
        mock_ctx.return_value.__enter__.return_value = mock_meeting_service
        
        # Trigger meeting detected signal manually
        payload = {"platform": "Zoom", "confidence": 0.95}
        # Publish MeetingDetected via event bus
        from app.background.meeting_detection.meeting_events import MeetingDetectedEvent
        detected_evt = MeetingDetectedEvent(user_id=1, payload=payload)
        srv.event_bus.publish(detected_evt)
        
        # Verify active session details
        active = manager.session_manager.get_active_session()
        assert active is not None
        assert active.platform == "Zoom"
        assert active.meeting_id == 99
        assert active.recording_state == "RECORDING"
        assert active.pipeline_state == "RECORDING"
        assert active.modules_health["audio"] == "healthy"
        
        # Verify start events got published
        assert EventType.SESSION_CREATED in received_events
        assert EventType.PIPELINE_STARTED in received_events
        assert EventType.RECORDING_STARTED in received_events
        
        # Trigger meeting ended signal manually
        from app.agent.events.event_models import MeetingStoppedEvent
        stop_evt = MeetingStoppedEvent(user_id=1, meeting_id=99)
        srv.event_bus.publish(stop_evt)
        
        # Verify session closed cleanly
        assert manager.session_manager.get_active_session() is None
        history = manager.session_manager.get_session_history()
        assert len(history) == 1
        assert history[0].pipeline_state == "COMPLETED"
        assert history[0].recording_state == "STOPPED"
        
        # Verify stop events got published
        assert EventType.RECORDING_STOPPED in received_events
        assert EventType.PIPELINE_COMPLETED in received_events
        assert EventType.SESSION_CLOSED in received_events

def test_duplicate_prevention(clean_recording_manager, mock_meeting_service):
    manager = clean_recording_manager
    srv = BackgroundService.get_instance()
    
    with patch("app.background.recording.pipeline_controller.get_background_meeting_service") as mock_ctx:
        mock_ctx.return_value.__enter__.return_value = mock_meeting_service
        
        # Start once
        assert manager.start_recording_pipeline("Slack Huddles") is True
        # Try duplicate start (should return False and prevent double meeting repository writes)
        assert manager.start_recording_pipeline("Slack Huddles") is False
        
        # Cleanup
        manager.stop_recording_pipeline()

def test_pipeline_fault_isolation(clean_recording_manager, mock_meeting_service):
    manager = clean_recording_manager
    
    # Simulate Audio failure to test recovery and isolation loops
    mock_meeting_service.start_meeting.side_effect = RuntimeError("Audio Loopback Capture Failed")
    
    with patch("app.background.recording.pipeline_controller.get_background_meeting_service") as mock_ctx:
        mock_ctx.return_value.__enter__.return_value = mock_meeting_service
        
        # Start recording
        manager.start_recording_pipeline("Discord")
        
        # Health state for audio should be flagged as failed, while other stages remain healthy/isolated
        active = manager.session_manager.get_active_session()
        assert active is not None
        assert active.modules_health["audio"] == "failed"
        assert active.modules_health["whisper"] == "healthy" # Isolated
        
        # Stop
        manager.stop_recording_pipeline()

def test_restart_recovery_behavior(clean_recording_manager, mock_meeting_service):
    manager = clean_recording_manager
    
    # Configure running meeting details
    running_meeting = MagicMock()
    running_meeting.id = 777
    mock_meeting_service._get_single_running_meeting.return_value = running_meeting

    with patch("app.background.recording.recording_manager.get_background_meeting_service") as mock_ctx:
        mock_ctx.return_value.__enter__.return_value = mock_meeting_service

        # Re-run recovery
        manager.recover_interrupted_sessions()

        # Active session should be successfully restored matching the running meeting id
        active = manager.session_manager.get_active_session()
        assert active is not None
        assert active.meeting_id == 777
        assert active.recording_state == "RECORDING"
        assert active.pipeline_state == "RECORDING"
        
        # Stop
        manager.stop_recording_pipeline()
