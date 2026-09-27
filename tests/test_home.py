import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    import datetime
    from app.database import Base, engine, SessionLocal
    from app.models import StoreDataset, Run, Deal
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # We need an active grocery dataset to render the badges and filters
    dataset = StoreDataset(
        store_name="ALDI",
        scraper_key="aldi",
        kind="grocery",
        status="success",
        trigger_mode="manual",
        flyer_start_date=datetime.date.today(),
        flyer_end_date=datetime.date.today() + datetime.timedelta(days=7),
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    )
    db.add(dataset)
    db.commit()

    run = Run(
        is_ready=True,
        run_date=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(run)
    db.commit()

    deal = Deal(
        run_id=run.id,
        store_name="ALDI",
        item_name="Apple",
        sale_price="1.99",
        category="Produce"
    )
    db.add(deal)
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
