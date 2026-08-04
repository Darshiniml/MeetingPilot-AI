import pytest
import logging
from fastapi.testclient import TestClient
from app.main import app
from app.agent_monitor.agent_logs import global_log_handler

@pytest.fixture
def client():
    return TestClient(app)

def test_rest_endpoints(client):
    # 1. Test status API
    response = client.get("/agent/status")
    assert response.status_code == 200
    data = response.json()
    assert "lifecycle_state" in data
    assert "status" in data
    
    # 2. Test health API
    response = client.get("/agent/health")
    assert response.status_code == 200
    data = response.json()
    assert "Background Service" in data
    assert "Meeting Detector" in data
    
    # 3. Test metrics API
    response = client.get("/agent/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_usage_percent" in data
    assert "memory_usage_percent" in data
    
    # 4. Test modules dependency API
    response = client.get("/agent/modules")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Background Agent"

def test_logs_endpoint_and_custom_handler(client):
    # Log a message to standard logger
    test_logger = logging.getLogger("test_module")
    test_logger.setLevel(logging.INFO)
    test_logger.warning("Test message for Agent Control Center log handler")
    
    # Verify the message got captured by our custom handler
    logs = global_log_handler.get_logs(module="test_module", limit=10)
    assert len(logs) > 0
    assert any("Test message for Agent Control Center" in l["message"] for l in logs)
    
    # Test GET logs endpoint
    response = client.get("/agent/logs?module=test_module")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any("Test message" in l["message"] for l in data)

def test_websocket_handshake(client):
    # Test WS handshake connection
    with client.websocket_connect("/agent/ws") as websocket:
        # Receive first JSON data update payload
        data = websocket.receive_json()
        assert "status" in data
        assert "health" in data
        assert "metrics" in data
        assert "logs" in data
