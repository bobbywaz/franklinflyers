import pytest
import datetime
from app.database import Base, engine, SessionLocal
from app.models import StoreDataset, StoreDeal, Run, Deal, PublishedSnapshotStore

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    now = datetime.datetime.now(datetime.UTC)
    today = now.date()

    # --- Home (Grocery) ---
    run = Run(run_date=now, is_ready=True)
    db.add(run)
    db.flush()
    db.add(Deal(run_id=run.id, store_name="ALDI", item_name="Milk", sale_price="$2.00", category="Dairy", score=10))
    g_dataset = StoreDataset(
        scraper_key="aldi", store_name="ALDI", kind="grocery",
        trigger_mode="manual", status="success",
        flyer_start_date=today, flyer_end_date=today,
        expires_at=now + datetime.timedelta(days=1)
    )
    db.add(g_dataset)
    db.flush()
    db.add(PublishedSnapshotStore(run_id=run.id, store_dataset_id=g_dataset.id, scraper_key="aldi", store_name="ALDI"))

    # --- Dispensaries ---
    d_dataset = StoreDataset(
        scraper_key="patriot_care", store_name="Patriot Care", kind="dispensary",
        trigger_mode="manual", status="success",
        flyer_start_date=today, flyer_end_date=today,
        expires_at=now + datetime.timedelta(days=1)
    )
    db.add(d_dataset)
    db.flush()
    db.add(StoreDeal(dataset_id=d_dataset.id, item_name="Gummies BOGO Free", sale_price="$25.00", description="Buy 1 Get 1 Free promotion"))

    # --- Pharmacies ---
    p_dataset_1 = StoreDataset(
        scraper_key="cvs_greenfield", store_name="CVS", kind="pharmacy",
        trigger_mode="manual", status="success",
        flyer_start_date=today, flyer_end_date=today,
        expires_at=now + datetime.timedelta(days=1)
    )
    db.add(p_dataset_1)
    db.flush()
    db.add(StoreDeal(dataset_id=p_dataset_1.id, item_name="Vitamins BOGO Free", sale_price="$10.00", description="Buy 1 Get 1 Free promotion"))

    p_dataset_2 = StoreDataset(
        scraper_key="walgreens_greenfield", store_name="Walgreens", kind="pharmacy",
        trigger_mode="manual", status="success",
        flyer_start_date=today, flyer_end_date=today,
        expires_at=now + datetime.timedelta(days=1)
    )
    db.add(p_dataset_2)
    db.flush()
    db.add(StoreDeal(dataset_id=p_dataset_2.id, item_name="Toothpaste", sale_price="$2.00", description="Save 50%"))

    # --- Movies ---
    # The wheel function parses `sale_price` for showtimes like '4:30 PM' or '5:00 PM'
    # Test `test_upcoming_wheel_movies_filters_and_caps` specifically tests with `ref_time = 16:15`
    # We want a showtime within 2.5 hours after 16:15 -> So 17:00 (5:00 PM) is perfect.
    m_dataset = StoreDataset(
        scraper_key="greenfield_garden_cinemas", store_name="Garden Cinemas", kind="movie",
        trigger_mode="manual", status="success",
        flyer_start_date=today, flyer_end_date=today,
        expires_at=now + datetime.timedelta(days=1)
    )
    db.add(m_dataset)
    db.flush()
    db.add(StoreDeal(dataset_id=m_dataset.id, item_name="Movie Title", sale_price="5:00 PM", description="Tickets"))

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)
