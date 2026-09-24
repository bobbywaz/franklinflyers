import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    from unittest.mock import patch, MagicMock
    with patch("app.main.get_active_grocery_datasets") as mock_get:
        mock_ds = MagicMock()
        mock_ds.store_name = "ALDI"
        mock_ds.scraper_key = "aldi"
        mock_ds.flyer_start_date = None
        mock_ds.flyer_end_date = None
        mock_get.return_value = [mock_ds]
        from app.models import Run
        with patch("app.main.Session.query") as mock_query:
            mock_run = MagicMock()
            mock_run.deals = [MagicMock(store_name="ALDI", item_name="Milk", sale_price="$2.00", category="Dairy", score=10)]
            mock_run.best_store = None
            mock_run.seasonal_info = None
            mock_run.recipe_idea = None
            mock_query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_run
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
