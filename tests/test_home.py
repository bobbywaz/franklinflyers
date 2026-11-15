import re
from starlette.testclient import TestClient
from app.main import app


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


def test_home_top_6_deals_showcase():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text
    if "Top 6 Deals Overall" in html:
        # Check that the banner states Top 6 Deals Overall
        assert "🔥 Top 6 Deals Overall" in html
        # Ensure that at most 6 deal-cards appear within top-overall-grid
        match = re.search(r'id="top-overall-grid">(.*?)<div id="top-overall-empty"', html, re.DOTALL)
        if match:
            cards = match.group(1).count('class="bg-gray-50 rounded border p-4 relative')
            assert cards <= 6

