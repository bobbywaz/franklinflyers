import datetime
from app.database import SessionLocal, Base, engine
from app.models import StoreDataset, StoreDeal, Run, Deal
from app.store_utils import utcnow

def seed_for_tests(db):
    now = utcnow()

    # Dispensary data
    dispensary_ds = StoreDataset(
        scraper_key="test_dispensary",
        store_name="Test Dispensary",
        kind="dispensary",
        trigger_mode="manual",
        status="success",
        flyer_start_date=now.date(),
        flyer_end_date=(now + datetime.timedelta(days=7)).date(),
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(dispensary_ds)
    db.flush()
    db.add(StoreDeal(dataset_id=dispensary_ds.id, item_name="Good Weed", sale_price="BOGO", description="Buy 1 Get 1"))

    # Movie data
    movie_ds = StoreDataset(
        scraper_key="test_movie",
        store_name="Test Movie",
        kind="movie",
        trigger_mode="manual",
        status="success",
        flyer_start_date=now.date(),
        flyer_end_date=(now + datetime.timedelta(days=7)).date(),
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(movie_ds)
    db.flush()
    db.add(StoreDeal(dataset_id=movie_ds.id, item_name="Movie", sale_price="5:15 PM", description="Tickets: url"))

    # Pharmacy data
    pharmacy_ds = StoreDataset(
        scraper_key="cvs_greenfield",
        store_name="CVS Pharmacy (Greenfield)",
        kind="pharmacy",
        trigger_mode="manual",
        status="success",
        flyer_start_date=now.date(),
        flyer_end_date=(now + datetime.timedelta(days=7)).date(),
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(pharmacy_ds)
    db.flush()
    db.add(StoreDeal(dataset_id=pharmacy_ds.id, item_name="Pills", sale_price="BOGO", description="Buy 1 Get 1"))

    # Home grocery data
    grocery_ds = StoreDataset(
        scraper_key="aldi",
        store_name="ALDI",
        kind="grocery",
        trigger_mode="manual",
        status="success",
        flyer_start_date=now.date(),
        flyer_end_date=(now + datetime.timedelta(days=7)).date(),
        started_at=now,
        finished_at=now,
        expires_at=now + datetime.timedelta(days=7),
    )
    db.add(grocery_ds)

    run = Run(run_date=now, is_ready=True)
    db.add(run)
    db.flush()
    db.add(Deal(run_id=run.id, store_name="ALDI", item_name="Eggs", sale_price="$1", category="Dairy", score=10))

    db.commit()
