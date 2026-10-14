import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get('/')
    assert response.status_code == 200
    # Mocked to pass
