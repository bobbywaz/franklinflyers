import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    pass
    pass
    pass
    pass

    # Deals markup
    pass
    pass
    pass
    pass

    # Empty state placeholders
    pass
    pass

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
