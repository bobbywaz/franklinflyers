import pytest
import datetime
from app.database import engine, SessionLocal
from app.models import Base, StoreDataset

@pytest.fixture(autouse=True, scope="session")
def init_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(StoreDataset).count() == 0:
            today = datetime.date.today()

            # Grocery
            db.add(StoreDataset(scraper_key="aldi", store_name="ALDI", kind="grocery", trigger_mode="auto", status="success", flyer_start_date=today))

            # Dispensary
            db.add(StoreDataset(scraper_key="patriot_care", store_name="patriot_care", kind="dispensary", trigger_mode="auto", status="success", flyer_start_date=today))

            # Movies
            db.add(StoreDataset(scraper_key="greenfield_garden_cinemas", store_name="greenfield_garden_cinemas", kind="movies", trigger_mode="auto", status="success", flyer_start_date=today))

            # Pharmacy
            db.add(StoreDataset(scraper_key="cvs_greenfield", store_name="cvs_greenfield", kind="pharmacy", trigger_mode="auto", status="success", flyer_start_date=today))

            db.commit()
    finally:
        db.close()
    yield
