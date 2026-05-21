import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Deal, FailedScrape, Run, StoreDataset
from app.scheduler import run_full_scrape, run_single_scrape
from app.store_utils import get_active_dataset_by_key


def future_window():
    start = datetime.date.today()
    end = start + datetime.timedelta(days=6)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    expires = now + datetime.timedelta(days=6)
    next_refresh = now + datetime.timedelta(days=5)
    return start, end, expires, next_refresh


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def mock_session_local(db_session):
    with patch("app.scheduler.SessionLocal", return_value=db_session):
        yield


@pytest.fixture(scope="function")
def mock_sync_jobs():
    with patch("app.scheduler._sync_dynamic_refresh_jobs"):
        yield


@pytest.mark.asyncio
async def test_run_full_scrape_persists_individual_results_and_publishes_snapshot(mock_session_local, mock_sync_jobs, db_session):
    flyer_start, flyer_end, expires_at, next_refresh_at = future_window()
    full_results = [
        {
            "scraper_key": "aldi",
            "store_name": "ALDI",
            "kind": "grocery",
            "status": "success",
            "error_message": None,
            "payload": {
                "scraper_key": "aldi",
                "store_name": "ALDI",
                "kind": "grocery",
                "deals": [{"name": "Apple", "price": "1.00", "description": "Crisp"}],
                "item_count": 1,
                "items_scraped_count": 48,
                "flyer_start_date": flyer_start,
                "flyer_end_date": flyer_end,
                "expires_at": expires_at,
                "next_refresh_at": next_refresh_at,
                "date_source": "extracted",
            },
        },
        {
            "scraper_key": "big_y",
            "store_name": "Big Y",
            "kind": "grocery",
            "status": "failed",
            "error_message": "Timeout",
            "payload": None,
        },
    ]

    with patch("app.scheduler.ScraperManager") as MockManager, patch("app.scheduler.GeminiAnalyzer") as MockAnalyzer:
        MockManager.return_value.run_full_batch = AsyncMock(return_value=full_results)
        MockAnalyzer.return_value.analyze_deals = AsyncMock(
            return_value={
                "scored_deals": [
                    {
                        "store_name": "ALDI",
                        "item_name": "Apple",
                        "sale_price": "1.00",
                        "category": "Produce",
                        "score": 9,
                        "explanation": "Great deal",
                    }
                ],
                "best_store": {
                    "store_name": "ALDI",
                    "summary": "Best value",
                    "strengths": ["Produce"],
                    "weaknesses": ["Limited"],
                    "score": 8,
                },
            }
        )

        run = await run_full_scrape(trigger_mode="scheduled_full")

    assert run is not None
    assert db_session.query(StoreDataset).count() == 2
    assert db_session.query(StoreDataset).filter(StoreDataset.scraper_key == "aldi").first().items_scraped_count == 48
    assert db_session.query(Run).count() == 1
    assert db_session.query(Deal).count() == 1
    assert db_session.query(FailedScrape).count() == 1
    assert db_session.query(FailedScrape).first().store_name == "Big Y"


@pytest.mark.asyncio
async def test_run_single_scrape_publishes_when_store_was_missing(mock_session_local, mock_sync_jobs, db_session):
    flyer_start, flyer_end, expires_at, next_refresh_at = future_window()
    result = {
        "scraper_key": "aldi",
        "store_name": "ALDI",
        "kind": "grocery",
        "status": "success",
        "error_message": None,
        "payload": {
            "scraper_key": "aldi",
            "store_name": "ALDI",
            "kind": "grocery",
            "deals": [{"name": "Apple", "price": "1.00", "description": "Crisp"}],
            "item_count": 1,
            "items_scraped_count": 48,
            "flyer_start_date": flyer_start,
            "flyer_end_date": flyer_end,
            "expires_at": expires_at,
            "next_refresh_at": next_refresh_at,
            "date_source": "extracted",
        },
    }

    with patch("app.scheduler.ScraperManager") as MockManager, patch("app.scheduler.GeminiAnalyzer") as MockAnalyzer:
        MockManager.return_value.run_single = AsyncMock(return_value=result)
        MockAnalyzer.return_value.analyze_deals = AsyncMock(
            return_value={"scored_deals": [], "best_store": None}
        )

        await run_single_scrape("aldi", trigger_mode="manual_single")

    latest_dataset = db_session.query(StoreDataset).order_by(StoreDataset.id.desc()).first()
    assert latest_dataset is not None
    assert latest_dataset.status == "success"
    assert db_session.query(StoreDataset).count() == 1
    assert db_session.query(Run).count() == 1


@pytest.mark.asyncio
async def test_failed_single_scrape_keeps_previous_active_data(mock_session_local, mock_sync_jobs, db_session):
    success_result = {
        "scraper_key": "aldi",
        "store_name": "ALDI",
        "kind": "grocery",
        "status": "success",
        "error_message": None,
        "payload": {
            "scraper_key": "aldi",
            "store_name": "ALDI",
            "kind": "grocery",
            "deals": [{"name": "Apple", "price": "1.00", "description": "Crisp"}],
            "item_count": 1,
            "items_scraped_count": 48,
            "flyer_start_date": datetime.date.today(),
            "flyer_end_date": datetime.date.today() + datetime.timedelta(days=6),
            "expires_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=6),
            "next_refresh_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=5),
            "date_source": "guessed",
        },
    }
    failed_result = {
        "scraper_key": "aldi",
        "store_name": "ALDI",
        "kind": "grocery",
        "status": "failed",
        "error_message": "No data returned",
        "payload": None,
    }

    with patch("app.scheduler.ScraperManager") as MockManager, patch("app.scheduler.GeminiAnalyzer") as MockAnalyzer:
        MockAnalyzer.return_value.analyze_deals = AsyncMock(return_value={"scored_deals": [], "best_store": None})
        manager_instance = MockManager.return_value
        manager_instance.run_single = AsyncMock(side_effect=[success_result, failed_result])

        await run_single_scrape("aldi", trigger_mode="manual_single")
        await run_single_scrape("aldi", trigger_mode="manual_single")

    active_dataset = get_active_dataset_by_key(db_session, "aldi")
    assert active_dataset is not None
    assert active_dataset.status == "success"
    assert db_session.query(StoreDataset).count() == 2
