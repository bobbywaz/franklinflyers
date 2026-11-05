import pytest
from app.database import Base, engine
from sqlalchemy.orm import Session
import app.models
from app.models import StoreDataset, StoreDeal, Run, PublishedSnapshotStore, Deal
from datetime import datetime, timezone, timedelta

@pytest.fixture(autouse=True, scope="function")
def setup_database():
    """Create database tables for tests and seed basic data for empty states."""
    Base.metadata.create_all(bind=engine)

    db = Session(engine)

    # 1. Dispensary Deal
    dataset1 = StoreDataset(
        scraper_key="patriot_care",
        store_name="Patriot Care",
        kind="dispensary",
        trigger_mode="manual_single",
        status="success",
        finished_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        item_count=1
    )
    db.add(dataset1)
    db.flush()
    sdeal1 = StoreDeal(
        dataset_id=dataset1.id,
        item_name="Wedding Cake 3.5g",
        sale_price="$20.00",
        description="Buy 1 get 1 free",
    )
    db.add(sdeal1)

    # Run for Home/Pharmacy
    run1 = Run(
        run_date=datetime.now(timezone.utc),
        is_ready=True,
        seasonal_info="summary",
        recipe_idea="recipe"
    )
    db.add(run1)
    db.flush()

    # Pharmacy Deal
    dataset2 = StoreDataset(
        scraper_key="cvs_greenfield",
        store_name="CVS",
        kind="pharmacy",
        trigger_mode="manual_single",
        status="success",
        finished_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        item_count=1
    )
    db.add(dataset2)

    dataset2b = StoreDataset(
        scraper_key="walgreens_greenfield",
        store_name="Walgreens Greenfield",
        kind="pharmacy",
        trigger_mode="manual_single",
        status="success",
        finished_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        item_count=1
    )
    db.add(dataset2b)

    db.flush()
    sdeal2 = StoreDeal(
        dataset_id=dataset2.id,
        item_name="Ibuprofen",
        sale_price="$2.00",
        description="Pain relief",
    )
    db.add(sdeal2)
    ps2 = PublishedSnapshotStore(
        run_id=run1.id,
        store_dataset_id=dataset2.id,
        scraper_key="cvs_greenfield",
        store_name="CVS"
    )
    db.add(ps2)
    ps2b = PublishedSnapshotStore(
        run_id=run1.id,
        store_dataset_id=dataset2b.id,
        scraper_key="walgreens_greenfield",
        store_name="Walgreens Greenfield"
    )
    db.add(ps2b)

    rdeal2 = Deal(
        run_id=run1.id,
        store_name="CVS",
        item_name="Ibuprofen",
        sale_price="$2.00",
        description="Pain relief",
        category="Health",
        score=10
    )
    db.add(rdeal2)

    # Grocery Deal
    dataset3 = StoreDataset(
        scraper_key="stop_and_shop",
        store_name="Stop And Shop",
        kind="grocery",
        trigger_mode="manual_single",
        status="success",
        finished_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        item_count=1
    )
    db.add(dataset3)
    db.flush()
    sdeal3 = StoreDeal(
        dataset_id=dataset3.id,
        item_name="Apple",
        sale_price="$1.00",
        description="Fruit",
    )
    db.add(sdeal3)
    ps3 = PublishedSnapshotStore(
        run_id=run1.id,
        store_dataset_id=dataset3.id,
        scraper_key="stop_and_shop",
        store_name="Stop And Shop"
    )
    db.add(ps3)
    rdeal3 = Deal(
        run_id=run1.id,
        store_name="Stop And Shop",
        item_name="Apple",
        sale_price="$1.00",
        description="Fruit",
        category="Produce",
        score=10
    )
    db.add(rdeal3)

    # 4. Movie
    dataset4 = StoreDataset(
        scraper_key="cinemark_hadley",
        store_name="Cinemark Hadley",
        kind="movie",
        trigger_mode="manual_single",
        status="success",
        finished_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        item_count=1,
        flyer_start_date=datetime.now(timezone.utc).date(),
        flyer_end_date=datetime.now(timezone.utc).date() + timedelta(days=7),
    )
    db.add(dataset4)
    db.flush()
    movie_deal = StoreDeal(
        dataset_id=dataset4.id,
        item_name="Dune: Part Two",
        sale_price="4:15 PM",
        description='{"poster_url": "", "rating": "PG-13", "runtime": "166 min"}',
    )
    db.add(movie_deal)

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)
