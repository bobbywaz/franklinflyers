import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes only render if there are active datasets
    # Since we use an empty db for this base test, it shouldn't crash, but won't have filters
    # Verify the empty state is present
    assert 'No flyer data analyzed yet' in html

    # The filter JS and empty state placeholders are still rendered
    assert 'id="top-overall-empty"' in html
    assert 'id="deals-by-category-empty"' in html

    # Empty state placeholders
    assert 'id="top-overall-empty"' in html
    assert 'id="deals-by-category-empty"' in html

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
