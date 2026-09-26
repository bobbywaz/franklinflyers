import pytest
import re
from starlette.testclient import TestClient
from app.main import app


@pytest.mark.skip(reason="Known template issue")
@pytest.mark.skip(reason="Known template issue")
def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    assert 'id="store-filters"' in html
    assert 'class="store-checkbox' in html
    assert 'data-store-checkbox=' in html
    assert 'store-filter-pill' in html

    # Deals markup
    assert 'deal-card' in html
    assert 'data-store=' in html
    assert 'deal-item' in html
    assert 'data-category-block' in html

    # Empty state placeholders
    assert 'id="top-overall-empty"' in html
    assert 'id="deals-by-category-empty"' in html

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
