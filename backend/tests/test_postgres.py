"""Optional integration gate against a dedicated disposable PostgreSQL database."""
import os
import pytest
from fastapi.testclient import TestClient
from app.bootstrap import migrate
from app.core.config import Settings
from app.main import create_app


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Dedicated PostgreSQL test database not configured")
def test_postgres_migration_seed_and_api():
    url = os.environ["TEST_POSTGRES_URL"]
    migrate(url)
    with TestClient(create_app(Settings(_env_file=None, database_url=url, demo_mode=True, app_api_key=""))) as client:
        assert client.get("/api/health/ready").status_code == 200
        data = client.get("/api/v1/workspace").json()
        assert len(data["incidents"]) >= 2
        linked = next(i for i in data["incidents"] if i["deployment_id"])
        assert client.get("/api/v1/incidents/" + linked["id"]).status_code == 200
