import pytest
import time
from unittest.mock import MagicMock
from app.background import BackgroundState, BackgroundService, ServiceManager
from app.agent.events.event_types import EventType

class MockWorkflowModule:
    """Mock background module that executes correctly."""
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        
    def start(self) -> None:
        self.started = True
        
    def stop(self) -> None:
        self.stopped = True

class CrashyModule:
    """Mock background module that crashes during startup to verify isolation."""
    def start(self) -> None:
        raise ValueError("Simulated module startup crash!")
        
    def stop(self) -> None:
        pass

def test_singleton_enforcement():
    # Retrieve instance
    srv1 = BackgroundService.get_instance()
    srv2 = BackgroundService.get_instance()
    assert srv1 is srv2
    
    # Test constructor throws direct exception
    with pytest.raises(RuntimeError):
        BackgroundService()

def test_startup_manager_mock():
    srv = BackgroundService.get_instance()
    # Check setup
    assert srv.startup_manager.enable_startup() is True
    assert srv.startup_manager.check_startup_status() is True
    assert srv.startup_manager.disable_startup() is True
    assert srv.startup_manager.check_startup_status() is False

def test_lifecycle_and_event_publishing():
    srv = BackgroundService.get_instance()
    
    # Track received EventBus messages
    received_events = []
    def on_event(event):
        received_events.append(event)
        
    # Subscribe to Agent lifecycle events
    srv.event_bus.subscribe(EventType.AGENT_STARTED, on_event)
    srv.event_bus.subscribe(EventType.AGENT_STOPPED, on_event)
    srv.event_bus.subscribe(EventType.AGENT_PAUSED, on_event)
    srv.event_bus.subscribe(EventType.AGENT_RESUMED, on_event)
    
    # Initialize service
    assert srv.state_manager.get_state() == BackgroundState.STOPPED
    
    # Start service
    ServiceManager.start_service()
    assert srv.state_manager.get_state() == BackgroundState.RUNNING
    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.AGENT_STARTED
    
    # Pause Service
    srv.pause()
    assert srv.state_manager.get_state() == BackgroundState.PAUSED
    assert len(received_events) == 2
    assert received_events[1].event_type == EventType.AGENT_PAUSED
    
    # Resume Service
    srv.resume()
    assert srv.state_manager.get_state() == BackgroundState.RUNNING
    assert len(received_events) == 3
    assert received_events[2].event_type == EventType.AGENT_RESUMED
    
    # Stop service
    ServiceManager.stop_service()
    assert srv.state_manager.get_state() == BackgroundState.STOPPED
    assert len(received_events) == 4
    assert received_events[3].event_type == EventType.AGENT_STOPPED

def test_module_registration_and_automatic_recovery():
    srv = BackgroundService.get_instance()
    
    mock_mod = MockWorkflowModule()
    crashy_mod = CrashyModule()
    
    # Register modules
    srv.register_module("mock_workflow", mock_mod)
    srv.register_module("crashy_analyzer", crashy_mod)
    
    # Start service
    ServiceManager.start_service()
    
    # Fault isolation check: mock_mod started successfully despite crashy_mod throwing exception
    assert mock_mod.started is True
    
    # Check metrics telemetry isolation counts
    health = srv.get_health_status()
    assert health["metrics"]["recovery_attempts"] == 1
    assert health["metrics"]["modules"]["mock_workflow"] == "running"
    assert health["metrics"]["modules"]["crashy_analyzer"] == "failed"
    
    # Stop service
    ServiceManager.stop_service()
    assert mock_mod.stopped is True

def test_restart_behavior():
    srv = BackgroundService.get_instance()
    
    # Start
    ServiceManager.start_service()
    assert srv.state_manager.get_state() == BackgroundState.RUNNING
    
    # Trigger restart
    ServiceManager.restart_service()
    assert srv.state_manager.get_state() == BackgroundState.RUNNING
    
    # Verify restart counter in metrics
    health = srv.get_health_status()
    assert health["metrics"]["restarts"] == 1
    
    # Stop
    ServiceManager.stop_service()
    assert srv.state_manager.get_state() == BackgroundState.STOPPED
