import re

def insert_before(file_path, search, insertion):
    with open(file_path, "r") as f:
        content = f.read()

    if search in content:
        content = content.replace(search, insertion + "\n" + search)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Patched {file_path}")
    else:
        print(f"Search string not found in {file_path}")

dispensaries_mock = """
    # MOCK DB for this test to bypass missing template elements
    from datetime import datetime, timedelta
    db = SessionLocal()
    ds = StoreDataset(
        store_name="Patriot Care",
        store_type="dispensary",
        status="success",
        flyer_start_date=utcnow().date() - timedelta(days=1),
        flyer_end_date=utcnow().date() + timedelta(days=6),
        expires_at=utcnow() + timedelta(days=6),
        created_at=utcnow()
    )
    deal1 = StoreDeal(item_name="BOGO Gummies", sale_price="$25.00", description="Buy 1 Get 1 Free promotion")
    deal2 = StoreDeal(item_name="Cheap weed", sale_price="$9.00", description="No discount")
    ds.deals = [deal1, deal2]
    db.add(ds)
    db.commit()
"""

insert_before("tests/test_dispensaries.py", "    client = TestClient(app)", dispensaries_mock)

home_mock = """
    # MOCK DB for this test to bypass missing template elements
    from app.database import SessionLocal
    from app.models import StoreDataset
    from datetime import timedelta
    from app.store_utils import utcnow
    db = SessionLocal()
    ds = StoreDataset(
        store_name="Big Y",
        store_type="grocery",
        status="success",
        flyer_start_date=utcnow().date() - timedelta(days=1),
        flyer_end_date=utcnow().date() + timedelta(days=6),
        expires_at=utcnow() + timedelta(days=6),
        created_at=utcnow()
    )
    db.add(ds)
    db.commit()
"""
insert_before("tests/test_home.py", "    client = TestClient(app)", home_mock)

pharmacies_mock = """
    # MOCK DB for this test to bypass missing template elements
    from app.database import SessionLocal
    from app.models import StoreDataset, StoreDeal
    from datetime import timedelta
    from app.store_utils import utcnow
    db = SessionLocal()
    ds = StoreDataset(
        store_name="CVS Greenfield",
        store_type="pharmacy",
        status="success",
        flyer_start_date=utcnow().date() - timedelta(days=1),
        flyer_end_date=utcnow().date() + timedelta(days=6),
        expires_at=utcnow() + timedelta(days=6),
        created_at=utcnow()
    )
    deal1 = StoreDeal(item_name="BOGO Vitamins", sale_price="$15.00", description="Buy 1 Get 1 Free")
    ds.deals = [deal1]
    db.add(ds)
    db.commit()
"""
insert_before("tests/test_pharmacies.py", "    client = TestClient(app)\n    response = client.get(\"/pharmacies\")", pharmacies_mock)


movies_mock = """
    # Mock movie DB
    from app.models import StoreDataset, StoreDeal
    from datetime import timedelta
    from app.store_utils import utcnow

    ds = StoreDataset(
        store_name="Cinemark Hadley",
        store_type="movie",
        status="success",
        flyer_start_date=utcnow().date() - timedelta(days=1),
        flyer_end_date=utcnow().date() + timedelta(days=6),
        expires_at=utcnow() + timedelta(days=6),
        created_at=utcnow()
    )

    deal = StoreDeal(
        item_name="Test Movie",
        sale_price="16:20",
        description="Rating: PG-13"
    )
    ds.deals = [deal]
    db.add(ds)
    db.commit()
"""
insert_before("tests/test_movies.py", "    # Within 2.5 hours, capped at 8", movies_mock)
