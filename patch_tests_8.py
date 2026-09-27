import re

def insert_after(file_path, search, insertion):
    with open(file_path, "r") as f:
        content = f.read()
    if search in content:
        content = content.replace(search, search + "\n" + insertion)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Patched {file_path}")
    else:
        print(f"Search string not found in {file_path}")


home_mock = """
    from datetime import datetime, timedelta
    from app.store_utils import utcnow
    from app.models import StoreDataset, StoreDeal
    from app.database import get_db
    db = next(get_db())
    ds_grocery = StoreDataset(store_name="Big Y", kind="grocery", scraper_key="big_y", status="success", flyer_start_date=utcnow().date() - timedelta(days=1), flyer_end_date=utcnow().date() + timedelta(days=6), expires_at=utcnow() + timedelta(days=6))
    ds_grocery.deals = [StoreDeal(item_name="Steak", sale_price="$5.99/lb", description="Sirloin")]
    db.add(ds_grocery)
    db.commit()
"""

insert_after("tests/test_home.py", "def test_home_store_filter_checkboxes():", home_mock)

dispensaries_mock = """
    from datetime import datetime, timedelta
    from app.store_utils import utcnow
    from app.models import StoreDataset, StoreDeal
    from app.database import get_db
    db = next(get_db())
    ds_dispensary = StoreDataset(store_name="Patriot Care", kind="dispensary", scraper_key="patriot_care", status="success", flyer_start_date=utcnow().date() - timedelta(days=1), flyer_end_date=utcnow().date() + timedelta(days=6), expires_at=utcnow() + timedelta(days=6))
    ds_dispensary.deals = [StoreDeal(item_name="Test Weed", sale_price="$25", description="BOGO Free")]
    db.add(ds_dispensary)
    db.commit()
"""
insert_after("tests/test_dispensaries.py", "def test_dispensaries_route_uncapped_and_zero_filler():", dispensaries_mock)

pharmacies_mock = """
    from datetime import datetime, timedelta
    from app.store_utils import utcnow
    from app.models import StoreDataset, StoreDeal
    from app.database import get_db
    db = next(get_db())
    ds_pharmacy = StoreDataset(store_name="CVS Greenfield", kind="pharmacy", scraper_key="cvs_greenfield", status="success", flyer_start_date=utcnow().date() - timedelta(days=1), flyer_end_date=utcnow().date() + timedelta(days=6), expires_at=utcnow() + timedelta(days=6))
    ds_pharmacy.deals = [StoreDeal(item_name="Vitamin C", sale_price="$10", description="BOGO")]
    db.add(ds_pharmacy)
    db.commit()
"""
insert_after("tests/test_pharmacies.py", "def test_pharmacies_route_ai_sections():", pharmacies_mock)

movies_mock = """
    from datetime import datetime, timedelta
    from app.store_utils import utcnow
    from app.models import StoreDataset, StoreDeal
    ds_movie = StoreDataset(store_name="Cinemark Hadley", kind="movie", scraper_key="cinemark_hadley", status="success", flyer_start_date=utcnow().date() - timedelta(days=1), flyer_end_date=utcnow().date() + timedelta(days=6), expires_at=utcnow() + timedelta(days=6))
    ds_movie.deals = [StoreDeal(item_name="Deadpool", sale_price="16:30", description="R")]
    db.add(ds_movie)
    db.commit()
"""
insert_after("tests/test_movies.py", "db = next(get_db())", movies_mock)
