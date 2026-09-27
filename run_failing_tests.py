import pytest
from app.main import app
from starlette.testclient import TestClient

def test_home():
    client = TestClient(app)
    response = client.get("/")
    print("test_home response size:", len(response.text))
    # print(response.text)

def test_dispensaries():
    client = TestClient(app)
    response = client.get("/dispensaries")
    print("test_dispensaries response size:", len(response.text))

def test_pharmacies():
    client = TestClient(app)
    response = client.get("/pharmacies")
    print("test_pharmacies response size:", len(response.text))

test_home()
test_dispensaries()
test_pharmacies()
