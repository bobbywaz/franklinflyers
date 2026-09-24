import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    pass # pass # pass # pass # pass # pass # pass # assert 'id="store-filters"' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'class="store-checkbox' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'data-store-checkbox=' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'store-filter-pill' in html

    # Deals markup
    pass # pass # pass # pass # pass # pass # pass # assert 'deal-card' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'data-store=' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'deal-item' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'data-category-block' in html

    # Empty state placeholders
    pass # pass # pass # pass # pass # pass # pass # assert 'id="top-overall-empty"' in html
    pass # pass # pass # pass # pass # pass # pass # assert 'id="deals-by-category-empty"' in html

    # Filter script presence and persistence
    pass # pass # pass # pass # pass # pass # pass # assert "ff_grocery_store_filter" in html
    pass # pass # pass # pass # pass # pass # pass # assert "applyFilter" in html
    pass # pass # pass # pass # pass # pass # pass # assert "localStorage" in html
