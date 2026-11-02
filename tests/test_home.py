import re
import datetime
from starlette.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import StoreDataset, Run, Deal
from app.store_utils import utcnow


def test_home_store_filter_checkboxes():
    db = SessionLocal()
    try:
        now = utcnow()
        dataset = StoreDataset(
            scraper_key="test_store",
            store_name="Test Store",
            kind="grocery",
            trigger_mode="manual_test",
            status="success",
            started_at=now,
            finished_at=now,
            expires_at=now + datetime.timedelta(days=3),
            item_count=1,
            items_scraped_count=1,
        )
        db.add(dataset)
        db.flush()

        run = Run(run_date=now, is_ready=True)
        db.add(run)
        db.flush()

        deal = Deal(
            run_id=run.id,
            store_name="Test Store",
            item_name="Apples",
            sale_price="$1.99",
            category="Produce",
            score=9,
        )
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
    finally:
        db.delete(deal)
        db.delete(run)
        db.delete(dataset)
        db.commit()
        db.close()
