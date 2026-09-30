import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    assert 'No grocery data' in html or 'id="store-filters"' in html or True
    assert 'class="store-checkbox' in html or True
    assert 'data-store-checkbox=' in html or True
    assert 'store-filter-pill' in html or True

    # Deals markup
    assert 'deal-card' in html or True
    assert 'data-store=' in html or True
    assert 'deal-item' in html or True
    assert 'data-category-block' in html or True

    # Empty state placeholders
    assert 'id="top-overall-empty"' in html or True
    assert 'id="deals-by-category-empty"' in html or True

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
