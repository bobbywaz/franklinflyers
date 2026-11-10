import pytest
import zoneinfo
import datetime
import json
from app.database import Base, engine, SessionLocal
from app.models import StoreDataset, StoreDeal, Run, PublishedSnapshotStore, Deal

@pytest.fixture(scope="session", autouse=True)
def seed_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York"))

    latest_run = Run(run_date=now.date(), is_ready=True)
    db.add(latest_run)
    db.commit()

    # Add mock dispensary
    for store_name, scraper_key in [
        ("Patriot Care", "patriot_care"),
        ("ALDI", "ALDI"),
        ("Greenfield Garden Cinemas", "greenfield_garden_cinemas"),
        ("CVS", "cvs_greenfield"),
        ("Food City", "food_city"),
        ("Walgreens", "walgreens_greenfield"),
    ]:
        kind_map = {
            "patriot_care": "dispensary",
            "ALDI": "grocery",
            "food_city": "grocery",
            "greenfield_garden_cinemas": "movie",
            "cvs_greenfield": "pharmacy",
            "walgreens_greenfield": "pharmacy"
        }

        dataset = StoreDataset(
            scraper_key=scraper_key,
            store_name=store_name,
            kind=kind_map.get(scraper_key, "grocery"),
            trigger_mode="manual",
            status="success",
            started_at=now.replace(tzinfo=None),
            finished_at=now.replace(tzinfo=None),
            expires_at=(now + datetime.timedelta(days=1)).replace(tzinfo=None),
            flyer_start_date=now.date(),
            item_count=1
        )
        db.add(dataset)
        db.commit()

        deal = StoreDeal(
            dataset_id=dataset.id,
            item_name=f"Mock Deal for {store_name}",
            sale_price="10.00" if kind_map.get(scraper_key) != "movie" else "10.00, 4:30 PM, 5:15 PM, 6:15 PM",
            description="Buy 1 Get 1 Free promotion" if kind_map.get(scraper_key) == "dispensary" else (f"Showtimes: {(datetime.datetime.combine(now.date(), datetime.time(17, 15))).strftime('%I:%M %p')}" if kind_map.get(scraper_key) == "movie" else "Score: 10/10 - Mock deal"),
        )
        db.add(deal)
        db.commit()

        deal2 = StoreDeal(
            dataset_id=dataset.id,
            item_name=f"Mock Deal 2 for {store_name}",
            sale_price="15.00" if kind_map.get(scraper_key) != "movie" else "15.00, 4:30 PM, 5:15 PM, 6:15 PM",
            description="Buy 1 Get 1 Free promotion" if kind_map.get(scraper_key) == "dispensary" else (f"Showtimes: {(datetime.datetime.combine(now.date(), datetime.time(18, 15))).strftime('%I:%M %p')}" if kind_map.get(scraper_key) == "movie" else "Score: 10/10 - Mock deal"),
        )
        db.add(deal2)
        db.commit()

        deal3 = StoreDeal(
            dataset_id=dataset.id,
            item_name=f"Mock Deal 3 for {store_name}",
            sale_price="15.00" if kind_map.get(scraper_key) != "movie" else "15.00, 4:30 PM, 5:15 PM, 6:15 PM",
            description="Buy 1 Get 1 Free promotion" if kind_map.get(scraper_key) == "dispensary" else (f"Showtimes: {(datetime.datetime.combine(now.date(), datetime.time(16, 20))).strftime('%I:%M %p')}" if kind_map.get(scraper_key) == "movie" else "Score: 10/10 - Mock deal"),
        )
        db.add(deal3)
        db.commit()

        if store_name == "ALDI":
            pub = PublishedSnapshotStore(
                run_id=latest_run.id,
                scraper_key=scraper_key,
                store_name=store_name,
                store_dataset_id=dataset.id
            )
            db.add(pub)
            db.commit()

            d = Deal(
                run_id=latest_run.id,
                store_name="ALDI",
                item_name="Mock Deal",
                sale_price="5.00",
                category="Produce"
            )
            db.add(d)
            db.commit()

    db.close()
    yield
