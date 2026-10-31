from fastapi.testclient import TestClient
from app.main import app

def test_pharmacies_route_ai_sections():
    client = TestClient(app)
    response = client.get("/pharmacies")
    html = response.text
    print(html)

test_pharmacies_route_ai_sections()
