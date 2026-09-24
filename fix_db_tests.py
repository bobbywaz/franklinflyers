from app.store_utils import utcnow
from datetime import timedelta
import re

def add_mock_to_setup(filepath, kind, store_name, item_name, extra_deals=""):
    with open(filepath, "r") as f:
        content = f.read()

    mock_code = f"""
    db = SessionLocal()
    from app.models import StoreDataset, StoreDeal, Run
    from app.store_utils import utcnow
    from datetime import timedelta

    now = utcnow()
    ds = StoreDataset(
        scraper_key="{kind}_test", store_name="{store_name}", kind="{kind}",
        trigger_mode="test", status="success",
        flyer_start_date=(now - timedelta(days=1)).date(),
        flyer_end_date=(now + timedelta(days=1)).date(),
        expires_at=now + timedelta(days=1),
        started_at=now, finished_at=now
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    deal = StoreDeal(dataset_id=ds.id, item_name="{item_name}", sale_price="$10.00", description="Test Deal")
    db.add(deal)
    {extra_deals}
    db.commit()

    run = Run(run_date=now, is_ready=True)
    db.add(run)
    db.commit()
    db.close()
"""

    # We replace `Base.metadata.create_all(bind=engine)` with the creation + mock
    content = content.replace("Base.metadata.create_all(bind=engine)", "Base.metadata.create_all(bind=engine)\n" + mock_code)
    with open(filepath, "w") as f:
        f.write(content)

add_mock_to_setup("tests/test_dispensaries.py", "dispensary", "Patriot Care", "Wedding Cake")
add_mock_to_setup("tests/test_home.py", "grocery", "ALDI", "Milk")

# For movies, we need specific movie properties
movie_extra = """
    deal2 = StoreDeal(dataset_id=ds.id, item_name="Upcoming Movie", sale_price="PG-13", description=(now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S-04:00"))
    db.add(deal2)
"""
add_mock_to_setup("tests/test_movies.py", "movie", "Garden Cinemas", "Test Movie", movie_extra)

pharm_extra = """
    ds2 = StoreDataset(
        scraper_key="walgreens_greenfield", store_name="Walgreens", kind="pharmacy",
        trigger_mode="test", status="success",
        flyer_start_date=(now - timedelta(days=1)).date(),
        flyer_end_date=(now + timedelta(days=1)).date(),
        expires_at=now + timedelta(days=1),
        started_at=now, finished_at=now
    )
    db.add(ds2)
    db.commit()
"""
add_mock_to_setup("tests/test_pharmacies.py", "pharmacy", "CVS", "Vitamin C", pharm_extra)
