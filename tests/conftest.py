import pytest
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models import Run, Deal, BestStore, StoreDataset, StoreDeal, PublishedSnapshotStore
import datetime

@pytest.fixture(scope="session", autouse=True)
def setup_db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run = Run(is_ready=True)
        db.add(run)
        db.commit()
        db.refresh(run)

        def add_mock_dataset(scraper_key, store_name, kind, deals, dates_delta_days=5):
            now = datetime.datetime.utcnow()
            dataset = StoreDataset(
                scraper_key=scraper_key,
                store_name=store_name,
                kind=kind,
                trigger_mode="manual",
                status="success",
                started_at=now,
                finished_at=now,
                flyer_start_date=now.date() - datetime.timedelta(days=1),
                flyer_end_date=now.date() + datetime.timedelta(days=dates_delta_days),
                expires_at=now + datetime.timedelta(days=dates_delta_days),
                item_count=len(deals),
                items_scraped_count=len(deals)
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)

            for item_name, sale_price, desc in deals:
                sd = StoreDeal(dataset_id=dataset.id, item_name=item_name, sale_price=sale_price, description=desc)
                db.add(sd)
            db.commit()

            pub = PublishedSnapshotStore(run_id=run.id, store_dataset_id=dataset.id, scraper_key=scraper_key, store_name=store_name)
            db.add(pub)
            db.commit()

        # 1. Dispensaries
        add_mock_dataset("patriot_care", "Patriot Care", "dispensary", [("Test Weed", "$10", "Good stuff")])
        Deal1 = Deal(run_id=run.id, store_name="Patriot Care", item_name="Test Weed", sale_price="$10", description="Good", category="Flower", score=10, explanation="cheap")
        db.add(Deal1)

        # 2. Pharmacies
        add_mock_dataset("cvs_greenfield", "CVS", "pharmacy", [("Test Pills", "$5", "Health")])
        add_mock_dataset("walgreens_greenfield", "Walgreens", "pharmacy", [("Test Pills 2", "$5", "Health")])
        Deal2 = Deal(run_id=run.id, store_name="CVS", item_name="Test Pills", sale_price="$5", description="Health", category="Health", score=10, explanation="cheap")
        db.add(Deal2)

        # 3. Grocery / Home
        add_mock_dataset("ALDI", "ALDI", "grocery", [("Test Apple", "$1", "Food")])
        Deal3 = Deal(run_id=run.id, store_name="ALDI", item_name="Test Apple", sale_price="$1", description="Food", category="Produce", score=10, explanation="cheap")
        db.add(Deal3)

        best_store = BestStore(run_id=run.id, store_name="ALDI", summary="Best", strengths="Cheap", weaknesses="None", score=10)
        db.add(best_store)

        best_store_disp = BestStore(run_id=run.id, store_name="Patriot Care", summary="Best Disp", strengths="Cheap", weaknesses="None", score=10)
        db.add(best_store_disp)

        # 4. Movies
        add_mock_dataset("greenfield_garden_cinemas", "Greenfield Garden Cinemas", "movie", [("Test Movie", "4:15 PM, 7:00 PM", "Tickets: http://test.com")])

        db.commit()

    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)
