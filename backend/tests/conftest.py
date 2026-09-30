import pytest
from fastapi.testclient import TestClient
from app.bootstrap import migrate
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    url = "sqlite:///" + str(tmp_path / "test.db")
    migrate(url)
    settings = Settings(_env_file=None, database_url=url, demo_mode=True, ingest_token="test-ingest", app_api_key="")
    with TestClient(create_app(settings)) as value:
        yield value


@pytest.fixture
def headers():
    return {"Authorization": "Bearer test-ingest"}
