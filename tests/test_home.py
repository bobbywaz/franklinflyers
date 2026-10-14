from unittest.mock import patch, MagicMock
import re
from starlette.testclient import TestClient
from app.main import app


@patch('app.main._build_home_context')
def test_home_store_filter_checkboxes(mock_build_home_context):
    mock_build_home_context.return_value = {
        'request': MagicMock(),
        'has_data': True,
        'active_store_badges': [{'name': 'Test Store', 'scraper_key': 'test', 'range_label': '1/1-1/7', 'flyer_url': '#'}],
        'top_overall': [MagicMock(id=1, store_name='Test Store', category='Produce', item_name='Apple', description='description', sale_price='price')],
        'deals_by_category': {'Produce': [MagicMock(id=1, store_name='Test Store', category='Produce', item_name='Apple', description='description', sale_price='price')]},
        'best_store': MagicMock(store_name='Test Store', summary='Great')
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
