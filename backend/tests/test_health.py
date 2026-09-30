from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app


def test_health_and_database_readiness():
    with TestClient(create_app(Settings(database_url="sqlite://", demo_mode=False))) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        ready = client.get("/api/health/ready")
        assert ready.status_code == 200
        assert ready.json()["database"] == "connected"
        assert client.get("/docs").status_code == 200
        assert "/api/health/ready" in client.get("/openapi.json").json()["paths"]


def test_database_failure_is_safe_and_does_not_break_liveness():
    app = create_app(Settings(database_url="sqlite://", demo_mode=False))
    with TestClient(app) as client:
        with patch.object(app.state.engine, "connect", side_effect=OperationalError(
            "secret connection details", {}, Exception("private password")
        )):
            response = client.get("/api/health/ready")
            assert response.status_code == 503
            assert response.json()["database"] == "unavailable"
            assert "password" not in response.text
            assert client.get("/api/health").status_code == 200


def test_cors_only_allows_configured_origin():
    with TestClient(create_app(Settings(database_url="sqlite://", demo_mode=False))) as client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        denied = client.get("/api/health", headers={"Origin": "https://untrusted.example"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "access-control-allow-origin" not in denied.headers
