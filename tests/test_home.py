import re
from starlette.testclient import TestClient
from app.main import app


def test_home_store_filter_checkboxes():
    from app.database import SessionLocal
    from app.models import StoreDataset, Run, PublishedSnapshotStore, Deal
    import datetime

    db = SessionLocal()
    ds = StoreDataset(
        scraper_key='test_grocery',
        store_name='ALDI',
        kind='grocery',
        trigger_mode='manual',
        status='success',
        item_count=1,
        items_scraped_count=1,
        flyer_start_date=datetime.date.today(),
        flyer_end_date=datetime.date.today(),
        expires_at=datetime.datetime.now() + datetime.timedelta(days=1)
    )
    db.add(ds)
    db.commit()

    run = Run(is_ready=True)
    db.add(run)
    db.commit()

    pss = PublishedSnapshotStore(
        run_id=run.id,
        store_dataset_id=ds.id,
        scraper_key='test_grocery',
        store_name='ALDI'
    )
    db.add(pss)

    deal = Deal(
        run_id=run.id,
        store_name='ALDI',
        item_name='test item',
        sale_price='$1.00',
        description='test desc',
        category='Produce',
        score=8,
        explanation='test exp'
    )
    db.add(deal)
    db.commit()

    client = TestClient(app)
    response = client.get("/")
    html = response.text

    db.delete(deal)
    db.delete(pss)
    db.delete(run)
    db.delete(ds)
    db.commit()
    db.close()

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
