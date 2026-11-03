import pytest
from app.database import engine, Base, SessionLocal

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)

    # Pre-seed DB to fix fragile tests that assume data exists
    from app.models import StoreDataset, Deal, Run, StoreDeal
    import datetime

    db = SessionLocal()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # 1. Dispensaries test data
    dataset1 = StoreDataset(
        scraper_key="patriot_care",
        store_name="Patriot Care",
        kind="dispensary",
        trigger_mode="manual_test",
        status="success",
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=3),
        item_count=1,
        items_scraped_count=1,
    )
    db.add(dataset1)
    db.commit()
    deal1 = StoreDeal(
        dataset_id=dataset1.id,
        item_name="Weed 22%",
        sale_price="$20",
        description="sale from $40", # 50% discount
    )
    db.add(deal1)
    db.commit()

    # 2. Home test data (needs a published run with an active dataset)
    run = Run(is_ready=True)
    db.add(run)
    db.commit()
    deal2 = Deal(
        run_id=run.id,
        store_name="ALDI",
        item_name="Steak",
        sale_price="$5",
        description="Good",
        category="Meat"
    )
    db.add(deal2)
    db.commit()
    dataset2 = StoreDataset(
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
    db.add(dataset2)
    db.commit()

    # 3. Movies test data
    dataset3 = StoreDataset(
        scraper_key="visit_greenfield",
        store_name="Visit Greenfield",
        kind="movie",
        trigger_mode="manual_test",
        status="success",
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=3),
        item_count=1,
        items_scraped_count=1,
    )
    db.add(dataset3)
    db.commit()
    deal3 = StoreDeal(
        dataset_id=dataset3.id,
        item_name="Spider-Man",
        sale_price="4:30 PM",
        description="test",
    )
    db.add(deal3)
    db.commit()

    # 4. Pharmacies test data
    dataset4 = StoreDataset(
        scraper_key="cvs_greenfield",
        store_name="CVS Pharmacy (Greenfield)",
        kind="pharmacy",
        trigger_mode="manual_test",
        status="success",
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=3),
        item_count=1,
        items_scraped_count=1,
    )
    db.add(dataset4)
    db.commit()
    dataset5 = StoreDataset(
        scraper_key="walgreens_greenfield",
        store_name="Walgreens (Greenfield)",
        kind="pharmacy",
        trigger_mode="manual_test",
        status="success",
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=3),
        item_count=1,
        items_scraped_count=1,
    )
    db.add(dataset5)
    db.commit()
    deal4 = StoreDeal(
        dataset_id=dataset4.id,
        item_name="Purified Water 24 pk",
        sale_price="2/ $7",
        description="Beverages",
    )
    db.add(deal4)
    db.commit()

    db.close()

    yield
    # We do not drop tables as some tests rely on state across functions
