import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():

    from datetime import datetime, timedelta
    from app.store_utils import utcnow
    from app.models import StoreDataset, StoreDeal
    from app.database import get_db
    db = next(get_db())
    ds_grocery = StoreDataset(store_name="Big Y", kind="grocery", scraper_key="big_y", status="success", flyer_start_date=utcnow().date() - timedelta(days=1), flyer_end_date=utcnow().date() + timedelta(days=6), expires_at=utcnow() + timedelta(days=6))
    ds_grocery.deals = [StoreDeal(item_name="Steak", sale_price="$5.99/lb", description="Sirloin")]
    db.add(ds_grocery)
    db.commit()

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
