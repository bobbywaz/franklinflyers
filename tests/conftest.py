import pytest
from app.database import Base, engine, init_db, SessionLocal
from app.models import StoreDataset, Deal, Run, StoreDeal
from datetime import datetime, timedelta
import json

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

    # Insert dummy data to make tests pass that assume a populated database
    db = SessionLocal()

    # 1. Home route dummy data
    run = Run(is_ready=True)
    db.add(run)
    db.commit()

    deal = Deal(run_id=run.id, store_name="Dummy Store", item_name="Dummy Item", category="Produce", score=10)
    db.add(deal)
    db.commit()

    grocery_dataset = StoreDataset(
        scraper_key="dummy_grocery",
        store_name="Dummy Store",
        kind="grocery",
        trigger_mode="manual",
        status="success",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(grocery_dataset)
    db.commit()

    # 2. Dispensaries route dummy data
    dispensary_dataset = StoreDataset(
        scraper_key="dummy_dispensary",
        store_name="Dummy Dispensary",
        kind="dispensary",
        trigger_mode="manual",
        status="success",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(dispensary_dataset)
    db.commit()

    d_deal = StoreDeal(
        dataset_id=dispensary_dataset.id,
        item_name="Dummy Item",
        description="Dummy Description 50% off",
    )
    db.add(d_deal)
    db.commit()

    # 3. Movies route dummy data
    import zoneinfo
    tz = zoneinfo.ZoneInfo("America/New_York")
    ref_time = datetime.now(tz).replace(hour=16, minute=15, second=0, microsecond=0)
    ref_time_str = (ref_time + timedelta(minutes=30)).strftime("%I:%M %p")

    movie_dataset = StoreDataset(
        scraper_key="dummy_movie",
        store_name="Dummy Movie",
        kind="movie",
        trigger_mode="manual",
        status="success",
        expires_at=datetime.utcnow() + timedelta(days=7),
        flyer_start_date=ref_time.date(),
        flyer_end_date=ref_time.date(),
    )
    db.add(movie_dataset)
    db.commit()

    m_deal = StoreDeal(
        dataset_id=movie_dataset.id,
        item_name="Dummy Movie 1",
        description="A cool movie",
        sale_price=ref_time_str
    )
    db.add(m_deal)
    db.commit()

    # 4. Pharmacies route dummy data
    pharmacy_dataset = StoreDataset(
        scraper_key="cvs_greenfield",
        store_name="CVS (Greenfield)",
        kind="pharmacy",
        trigger_mode="manual",
        status="success",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(pharmacy_dataset)
    db.commit()

    walgreens_dataset = StoreDataset(
        scraper_key="walgreens_greenfield",
        store_name="Walgreens (Greenfield)",
        kind="pharmacy",
        trigger_mode="manual",
        status="success",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(walgreens_dataset)
    db.commit()

    p_deal = StoreDeal(
        dataset_id=pharmacy_dataset.id,
        item_name="Dummy Pharmacy Item",
        description="description",
        sale_price="$10.00",
    )
    db.add(p_deal)
    db.commit()

    db.close()

    yield
