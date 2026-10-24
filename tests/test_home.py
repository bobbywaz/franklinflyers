import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    from app.database import engine
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200