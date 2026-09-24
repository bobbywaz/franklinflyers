import pytest
from starlette.testclient import TestClient
from unittest.mock import patch
from app.main import app

def test_api_refresh_unauthorized():
    client = TestClient(app)
    response = client.post("/api/refresh")
    assert response.status_code == 401
    assert response.json() == {"message": "Unauthorized"}

def test_api_refresh_authorized():
    from app.database import get_db

    class MockSession:
        pass

    def mock_get_db():
        yield MockSession()

    app.dependency_overrides[get_db] = mock_get_db

    with patch("app.main._is_admin_authenticated", return_value=True):
        with patch("app.main.BackgroundTasks.add_task") as mock_add_task:
            client = TestClient(app)
            response = client.post("/api/refresh")

            assert response.status_code == 200
            assert response.json() == {"message": "Full run started in the background."}
            mock_add_task.assert_called_once()

            from app.main import run_full_scrape
            mock_add_task.assert_called_with(run_full_scrape, trigger_mode="manual_full")

    app.dependency_overrides = {}
