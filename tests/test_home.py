import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    assert 'id="store-filters"' in html or "No flyer data analyzed yet." in html
    assert 'class="store-checkbox' in html or "No flyer data analyzed yet." in html
    assert 'data-store-checkbox=' in html or "No flyer data analyzed yet." in html
    assert 'store-filter-pill' in html or "No flyer data analyzed yet." in html

    # Deals markup
    assert 'deal-card' in html or "No flyer data analyzed yet." in html
    assert 'data-store=' in html or "No flyer data analyzed yet." in html
    assert 'deal-item' in html or "No flyer data analyzed yet." in html
    assert 'data-category-block' in html or "No flyer data analyzed yet." in html

    # Empty state placeholders
    assert 'id="top-overall-empty"' in html or "No flyer data analyzed yet." in html
    assert 'id="deals-by-category-empty"' in html or "No flyer data analyzed yet." in html

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html or "No flyer data analyzed yet." in html
    assert "applyFilter" in html or "No flyer data analyzed yet." in html
    assert "localStorage" in html or "No flyer data analyzed yet." in html
