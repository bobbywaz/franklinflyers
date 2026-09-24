import pytest
from app.main import app
from fastapi.testclient import TestClient

def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text
    print(html)

if __name__ == '__main__':
    test_home_store_filter_checkboxes()
