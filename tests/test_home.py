import re
from starlette.testclient import TestClient
from app.main import app

def test_home_store_filter_checkboxes():
    # Insert mock data to render the blocks
    from app.database import Base, SessionLocal, engine
    Base.metadata.create_all(bind=engine)
    from app.models import StoreDataset, Run, Deal, PublishedSnapshotStore
    from app.store_utils import utcnow
    import datetime

    db = SessionLocal()
    now = utcnow()
    ds = StoreDataset(
        scraper_key="ALDI",
        store_name="ALDI",
        kind="grocery",
        trigger_mode="manual_test",
        status="success",
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=3),
        item_count=1,
        items_scraped_count=1,
    )
    db.add(ds)
    db.commit()

    run = Run(
        run_date=now,
        is_ready=True,
    )
    db.add(run)
    db.commit()

    deal = Deal(
        run_id=run.id,
        store_name="ALDI",
        item_name="Eggs",
        sale_price="$2.99",
        description="Dozen eggs",
        category="Dairy",
        score=9
    )
    db.add(deal)

    pub_store = PublishedSnapshotStore(
        run_id=run.id,
        store_dataset_id=ds.id,
        scraper_key="ALDI",
        store_name="ALDI"
    )
    db.add(pub_store)
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
