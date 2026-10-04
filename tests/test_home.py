import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    from app.database import get_db, SessionLocal
    from app.models import StoreDataset, Run, Deal
    from app.store_utils import utcnow
    import datetime
    db = SessionLocal()
    now = utcnow()
    if not db.query(StoreDataset).filter_by(scraper_key="aldi").first():
        run = Run(is_ready=True)
        db.add(run)
        db.commit()
        ds = StoreDataset(scraper_key="aldi", store_name="ALDI", kind="grocery", trigger_mode="manual_single", status="success", flyer_start_date=now.date(), flyer_end_date=(now + datetime.timedelta(days=7)).date(), expires_at=now + datetime.timedelta(days=7))
        db.add(ds)
        db.commit()
        deal = Deal(run_id=run.id, store_name="ALDI", item_name="Bread", sale_price="$1", description="Cheap bread", category="Pantry", score=10)
        db.add(deal)
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
