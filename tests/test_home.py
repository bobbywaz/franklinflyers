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

    # The filter JS is still rendered, but the empty state placeholders are within
    # the has_data block, so they will not be present.
    assert 'id="top-overall-empty"' not in html
    assert 'id="deals-by-category-empty"' not in html

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
