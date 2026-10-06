from app.database import init_db
init_db()
import datetime
from sqlalchemy import create_engine
from app.models import Base
from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import StoreDataset, Run, Deal, BestStore, PublishedSnapshotStore
from app.database import SessionLocal

db = SessionLocal()

run = Run(is_ready=True)
db.add(run)
db.commit()

bs = BestStore(run_id=run.id, store_name="Test Store 1", score=10)
db.add(bs)
for i in range(10):
    d = Deal(run_id=run.id, store_name="Test Store 1", item_name=f"Item {i}", category="Pantry")
    db.add(d)

ds1 = StoreDataset(scraper_key="test1", store_name="Test Store 1", kind="grocery", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7))
ds2 = StoreDataset(scraper_key="test2", store_name="Test Store 2", kind="grocery", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7))

ds3 = StoreDataset(scraper_key="test3", store_name="Dispo 1", kind="dispensary", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7))
ds4 = StoreDataset(scraper_key="test4", store_name="Dispo 2", kind="dispensary", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7))

ds5 = StoreDataset(scraper_key="test5", store_name="Pharm 1", kind="pharmacy", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7))

ds6 = StoreDataset(scraper_key="test6", store_name="Movie 1", kind="movie", trigger_mode="manual", status="success", expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7), flyer_start_date=datetime.datetime.utcnow().date())


db.add_all([ds1, ds2, ds3, ds4, ds5, ds6])
db.commit()

p1 = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds1.id, scraper_key="test1", store_name="Test Store 1")
p2 = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds2.id, scraper_key="test2", store_name="Test Store 2")
p3 = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds3.id, scraper_key="test3", store_name="Dispo 1")
p5 = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds5.id, scraper_key="test5", store_name="Pharm 1")
p6 = PublishedSnapshotStore(run_id=run.id, store_dataset_id=ds6.id, scraper_key="test6", store_name="Movie 1")
db.add_all([p1, p2, p3, p5, p6])
db.commit()

d1 = Deal(run_id=run.id, store_name="Dispo 1", item_name=f"Weed 1", category="Flower", score=10)
d2 = Deal(run_id=run.id, store_name="Pharm 1", item_name=f"Pill 1", category="Pharmacy", score=10)
d3 = Deal(run_id=run.id, store_name="Movie 1", item_name=f"Movie 1", category="Movie", score=10, description="16:00, 16:30, 20:00")
db.add_all([d1, d2, d3])
db.commit()

db.close()
