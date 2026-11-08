import pytest
from app.database import Base, engine, SessionLocal
from app.models import StoreDataset, StoreDeal, Run, Deal, PublishedSnapshotStore
from app.store_utils import utcnow
from datetime import timedelta
import datetime

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = utcnow()
    try:
        # Dispensary seed
        ds = StoreDataset(
            scraper_key="patriot_care",
            store_name="Patriot Care",
            kind="dispensary",
            trigger_mode="manual",
            status="success",
            started_at=now,
            finished_at=now,
            expires_at=now + timedelta(days=7)
        )
        db.add(ds)
        db.flush()

        d1 = StoreDeal(dataset_id=ds.id, item_name="Deal 1", sale_price="BOGO", description="Sale from $10.00")
        d2 = StoreDeal(dataset_id=ds.id, item_name="Deal 2", sale_price="30% off", description="Sale from $10.00")
        d3 = StoreDeal(dataset_id=ds.id, item_name="Deal 3", sale_price="$2.00", description="Sale from $10.00")
        d4 = StoreDeal(dataset_id=ds.id, item_name="Deal 4", sale_price="$3.00", description="Sale from $10.00")
        db.add_all([d1, d2, d3, d4])

        # Home seed
        run = Run(is_ready=True, run_date=datetime.datetime.now(datetime.timezone.utc))
        db.add(run)
        db.flush()

        gds = StoreDataset(
            scraper_key="Stop & Shop",
            store_name="Stop & Shop",
            kind="grocery",
            trigger_mode="manual",
            status="success",
            started_at=now,
            finished_at=now,
            flyer_start_date=now.date(),
            flyer_end_date=(now + timedelta(days=7)).date(),
            expires_at=now + timedelta(days=7)
        )
        db.add(gds)
        db.flush()
        ps = PublishedSnapshotStore(run_id=run.id, store_dataset_id=gds.id, scraper_key="Stop & Shop", store_name="Stop & Shop")
        db.add(ps)
        gd1 = Deal(run_id=run.id, store_name="Stop & Shop", item_name="GDeal", sale_price="$1.00", category="Produce", description="desc", score=8)
        db.add(gd1)

        # Movies seed
        mds = StoreDataset(
            scraper_key="cinemark_hadley",
            store_name="Cinemark at Hampshire Mall (Hadley)",
            kind="movie",
            trigger_mode="manual",
            status="success",
            started_at=now,
            finished_at=now,
            flyer_start_date=now.date(),
            flyer_end_date=(now + timedelta(days=1)).date(),
            expires_at=now + timedelta(days=7)
        )
        db.add(mds)
        db.flush()

        md1 = StoreDeal(dataset_id=mds.id, item_name="Movie", sale_price="4:30 PM, 5:30 PM, 6:30 PM", description="Tickets: http://test.com")
        db.add(md1)

        # Pharmacies seed
        pds = StoreDataset(
            scraper_key="cvs_greenfield",
            store_name="CVS Pharmacy",
            kind="pharmacy",
            trigger_mode="manual",
            status="success",
            started_at=now,
            finished_at=now,
            expires_at=now + timedelta(days=7)
        )
        db.add(pds)
        db.flush()

        pd1 = StoreDeal(dataset_id=pds.id, item_name="PDeal", sale_price="BOGO", description="desc")
        pd2 = StoreDeal(dataset_id=pds.id, item_name="PDeal2", sale_price="50% off", description="desc")
        pd3 = StoreDeal(dataset_id=pds.id, item_name="PDeal3", sale_price="$11 off 2 online coupon", description="desc")
        pd4 = StoreDeal(dataset_id=pds.id, item_name="PDeal4", sale_price="$4 off 1", description="desc")
        db.add_all([pd1, pd2, pd3, pd4])

        pds2 = StoreDataset(
            scraper_key="walgreens_greenfield",
            store_name="Walgreens",
            kind="pharmacy",
            trigger_mode="manual",
            status="success",
            started_at=now,
            finished_at=now,
            expires_at=now + timedelta(days=7)
        )
        db.add(pds2)

        db.commit()
    finally:
        db.close()

    yield
