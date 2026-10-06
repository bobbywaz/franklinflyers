import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    from datetime import datetime, timedelta, timezone
    from app.database import SessionLocal
    from app.models import StoreDataset, StoreDeal, Run, PublishedSnapshotStore, Deal

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    ds = StoreDataset(
        scraper_key="aldi",
        store_name="ALDI",
        kind="grocery",
        trigger_mode="manual_single",
        status="success",
        flyer_start_date=(now - timedelta(days=1)).date(),
        flyer_end_date=(now + timedelta(days=6)).date(),
        expires_at=now + timedelta(days=6),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    run = Run(is_ready=True)
    db.add(run)
    db.commit()
    db.refresh(run)

    pss = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds.id, scraper_key="aldi", store_name="ALDI")

    deal1 = Deal(
        run_id=run.id,
        store_name="ALDI",
        item_name="Super High Score Deal",
        description="Sale from $50.00",
        sale_price="$10.00",
        score=10,
        category="Produce"
    )
    db.add_all([pss, deal1])
    db.commit()
    db.close()

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
