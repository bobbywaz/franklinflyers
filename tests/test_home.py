import re
from starlette.testclient import TestClient
from app.main import app




def test_home_store_filter_checkboxes():
    import datetime
    from app.database import SessionLocal, init_db, Base, engine
    from app.models import StoreDataset, Run, Deal, PublishedSnapshotStore

    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()

    ref_time = datetime.datetime.utcnow()

    dataset = StoreDataset(
        scraper_key="aldi",
        store_name="ALDI",
        kind="grocery",
        trigger_mode="manual",
        status="success",
        flyer_start_date=ref_time.date(),
        flyer_end_date=ref_time.date() + datetime.timedelta(days=7),
        expires_at=ref_time + datetime.timedelta(days=7),
        finished_at=ref_time
    )

    run = Run(is_ready=True)
    deal = Deal(store_name="ALDI", item_name="Test Item", category="Produce", score=8)
    run.deals.append(deal)
    run.published_stores.append(PublishedSnapshotStore(scraper_key="aldi", store_name="ALDI", dataset=dataset))

    db.add(dataset)
    db.add(run)
    db.commit()

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    db.close()

    # Store filters container and checkboxes
    assert 'id="store-filters"' in html
    assert 'id="store-filters"' in html
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
