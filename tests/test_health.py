import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import get_settings


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_health_endpoint(client):
    """Test GET /health returns 200 and expected schema."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    settings = get_settings()

    assert data["status"] == "ok"
    assert data["environment"] == settings.ENVIRONMENT
    assert data["version"] == settings.VERSION

    # Verify timestamp parses as valid ISO datetime
    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    assert isinstance(timestamp, datetime)


def test_api_v1_health_endpoint(client):
    """Test GET /api/v1/health returns 200 and expected schema."""
    settings = get_settings()
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] == settings.ENVIRONMENT
    assert data["version"] == settings.VERSION
    assert "timestamp" in data
