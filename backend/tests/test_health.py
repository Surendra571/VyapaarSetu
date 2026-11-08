from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint responds with basic application metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "VyapaarSetu"
    assert data["status"] == "operational"
    assert data["health_check"] == "/api/v1/health"


def test_health_check_healthy_when_database_connected():
    """Verify health endpoint reports healthy when database responds."""
    mock_db_status = {
        "connected": True,
        "latency_ms": 1.25,
        "message": "Database is reachable and operational.",
        "error": None,
    }
    with patch("app.api.v1.endpoints.health.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_db_status
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "VyapaarSetu"
        assert data["database"]["connected"] is True
        assert data["database"]["latency_ms"] == 1.25


def test_health_check_degraded_when_database_offline():
    """Verify health endpoint reports degraded gracefully when database is offline."""
    mock_db_status = {
        "connected": False,
        "latency_ms": 0.5,
        "message": "Database host 127.0.0.1:5432 is unreachable or offline.",
        "error": "ConnectionRefusedOrTimedOut",
    }
    with patch("app.api.v1.endpoints.health.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_db_status
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["connected"] is False
        assert "unreachable" in data["database"]["message"]
