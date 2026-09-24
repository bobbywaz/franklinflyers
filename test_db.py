from app.database import SessionLocal
from app.models import StoreDataset, StoreDeal
from datetime import datetime, timedelta

def add_mock_data():
    db = SessionLocal()
    dataset = StoreDataset(
        scraper_key="test_dispensary",
        store_name="Test Dispensary",
        kind="dispensary",
        trigger_mode="manual",
        status="success",
        flyer_start_date=(datetime.now() - timedelta(days=1)).date(),
        flyer_end_date=(datetime.now() + timedelta(days=1)).date(),
        expires_at=datetime.now() + timedelta(days=1),
        started_at=datetime.now(),
        finished_at=datetime.now()
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    deal1 = StoreDeal(
        dataset_id=dataset.id,
        item_name="Wedding Cake 3.5g",
        description="Sale from $40.00",
        sale_price="$28.00"
    )
    deal2 = StoreDeal(
        dataset_id=dataset.id,
        item_name="Grandpa's Cookies 1g",
        description="Regular",
        sale_price="$9.00"
    )
    db.add_all([deal1, deal2])
    db.commit()
    db.close()
