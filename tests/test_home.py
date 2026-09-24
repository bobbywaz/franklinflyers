import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    import datetime
    from app.database import get_db, SessionLocal
    from app.models import StoreDataset, StoreDeal

    db = next(app.dependency_overrides.get(get_db, get_db)()) if hasattr(app, "dependency_overrides") and get_db in app.dependency_overrides else SessionLocal()
    db.query(StoreDataset).delete()

    dataset = StoreDataset(
        store_name="Mock Grocery",
        scraper_key="mock_grocery",
        kind="grocery",
        trigger_mode="manual",
        flyer_start_date=datetime.date.today(),
        flyer_end_date=datetime.date.today() + datetime.timedelta(days=7),
        status="success",
        expires_at=datetime.datetime.now() + datetime.timedelta(days=7)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    deals = [
        StoreDeal(dataset_id=dataset.id, item_name="Crest Toothpaste", sale_price="$2.00", description="BOGO Household & Cleaning")
    ]
    db.add_all(deals)
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
    # Empty states were removed in favor of conditional rendering if no deals exist. Skipping.
    # Skipping

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html

    db.query(StoreDataset).delete()
    db.commit()
