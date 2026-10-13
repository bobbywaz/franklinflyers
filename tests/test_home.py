import re
from starlette.testclient import TestClient
from app.main import app


from unittest.mock import patch

from unittest.mock import patch, MagicMock

@patch("app.main._build_home_context")
def test_home_store_filter_checkboxes(mock_context):
    mock_context.return_value = {
        "has_data": True,
        "active_store_badges": [{"name": "ALDI", "flyer_url": "#"}],
        "top_overall": [{"store_name": "ALDI", "category": "Test", "item_name": "Test", "description": "Test", "sale_price": "$1", "score": 10}],
        "deals_by_category": {"Test": [{"store_name": "ALDI", "category": "Test", "item_name": "Test", "description": "Test", "sale_price": "$1", "score": 10}]}, "has_data": True,
        "best_store": {"store_name": "ALDI", "score": 10, "summary": "Great", "strengths": "Price", "weaknesses": "None"},
        "seasonal_guide": None,
        "recipe_idea": None,
        "latest_run": None,
        "store_colors": {},
        "store_flyers": {}
    }
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
