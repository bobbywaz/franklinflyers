import re
from starlette.testclient import TestClient
from app.main import app










def test_home_store_filter_checkboxes():
    from app.database import Base, engine, get_db
    from app.models import StoreDataset, StoreDeal, Run, PublishedSnapshotStore
    import datetime
    from app.main import app as main_app
    from starlette.testclient import TestClient

    # Need a dataset to make the store-filters render
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    ds = StoreDataset(
        scraper_key='aldi',
        store_name='ALDI',
        kind='grocery',
        trigger_mode='manual',
        status='success',
        started_at=datetime.datetime.utcnow(),
        finished_at=datetime.datetime.utcnow(),
        flyer_start_date=datetime.datetime.utcnow().date(),
        flyer_end_date=(datetime.datetime.utcnow() + datetime.timedelta(days=7)).date(),
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    deal = StoreDeal(
        dataset=ds,
        item_name='Apple',
        sale_price='1.99',
        description='Fresh'
    )
    db.add(ds)
    db.add(deal)
    db.commit()

    run = Run(
        run_date=datetime.datetime.utcnow(),
        is_ready=True
    )
    db.add(run)
    db.commit()

    # We need deals json to be stored in the Run
    run.best_store_json = '{"store_name": "ALDI"}'
    run.top_overall_json = '[{"store_name": "ALDI", "category": "Produce", "item_name": "Apple", "sale_price": "1.99", "score": 10}]'
    run.deals_by_category_json = '{"Produce": [{"store_name": "ALDI", "category": "Produce", "item_name": "Apple", "sale_price": "1.99", "score": 10}]}'

    snapshot_store = PublishedSnapshotStore(
        run_id=run.id,
        store_dataset_id=ds.id,
        scraper_key='aldi',
        store_name='ALDI'
    )
    db.add(snapshot_store)
    db.commit()

    # Clear cache
    import app.main
    app.main._homepage_cache = {}

    client = TestClient(main_app)
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


    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
