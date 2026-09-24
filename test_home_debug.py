from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/")
print("=" * 80)
print(response.text)
print("=" * 80)
