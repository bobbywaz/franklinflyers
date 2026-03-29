import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

def test_trigger_refresh():
    with patch("app.main.run_scrape_and_analyze") as mock_run:
        response = client.post("/api/refresh")

        assert response.status_code == 200
        assert response.json() == {"message": "Scrape process started in the background."}

        # TestClient runs background tasks immediately after returning response
        mock_run.assert_called_once()
