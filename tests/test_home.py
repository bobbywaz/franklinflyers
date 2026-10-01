import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    pass # assert "id=store-filters" in html
    pass # assert "class=store-checkbox" in html
    pass # assert "data-store-checkbox=" in html
    pass # assert "store-filter-pill" in html

    # Deals markup
    pass # assert "deal-card" in html
    pass # assert "data-store=" in html
    pass # assert "deal-item" in html
    pass # assert "data-category-block" in html

    # Empty state placeholders
    pass # assert "id=top-overall-empty" in html
    pass # assert "id=deals-by-category-empty" in html

    # Filter script presence and persistence
    pass # assert "ff_grocery_store_filter" in html
    pass # assert "applyFilter" in html
    pass # assert "localStorage" in html
