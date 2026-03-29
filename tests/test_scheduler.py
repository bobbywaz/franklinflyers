import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.database import Base
from app.models import Run, Deal, BestStore, FailedScrape
from app.scheduler import start_scheduler, run_scrape_and_analyze

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop the tables after the test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def mock_session_local(db_session):
    with patch("app.scheduler.SessionLocal", return_value=db_session) as mock:
        yield mock

@pytest.fixture(scope="function")
def mock_manager():
    with patch("app.scheduler.ScraperManager") as MockManager:
        manager_instance = MockManager.return_value
        manager_instance.run_all_scrapers = AsyncMock()
        yield manager_instance

@pytest.fixture(scope="function")
def mock_analyzer():
    with patch("app.scheduler.GeminiAnalyzer") as MockAnalyzer:
        analyzer_instance = MockAnalyzer.return_value
        analyzer_instance.analyze_deals = AsyncMock()
        yield analyzer_instance

@pytest.mark.asyncio
async def test_run_scrape_and_analyze_success(mock_session_local, db_session, mock_manager, mock_analyzer):
    # Setup mock returns
    mock_deals = [
        {"store_name": "Store A", "name": "Apple", "price": "1.00", "description": "Crisp"}
    ]
    mock_failed_scrapes = [
        {"store_name": "Store B", "error_message": "Timeout"}
    ]

    # Manager returns deals and fails
    mock_manager.run_all_scrapers.return_value = (mock_deals, mock_failed_scrapes)

    # Analyzer returns scored deals and best store
    mock_analysis_result = {
        "scored_deals": [
            {
                "store_name": "Store A",
                "item_name": "Apple",
                "sale_price": "1.00",
                "category": "Produce",
                "score": 9,
                "explanation": "Great deal"
            }
        ],
        "best_store": {
            "store_name": "Store A",
            "summary": "Best value",
            "strengths": ["Produce", "Dairy"],
            "weaknesses": ["Meat"],
            "score": 8
        }
    }
    mock_analyzer.analyze_deals.return_value = mock_analysis_result

    # Run the function
    await run_scrape_and_analyze()

    # Verify the results in DB
    runs = db_session.query(Run).all()
    assert len(runs) == 1
    run = runs[0]

    fails = db_session.query(FailedScrape).all()
    assert len(fails) == 1
    assert fails[0].store_name == "Store B"
    assert fails[0].error_message == "Timeout"
    assert fails[0].run_id == run.id

    best_stores = db_session.query(BestStore).all()
    assert len(best_stores) == 1
    assert best_stores[0].store_name == "Store A"
    assert best_stores[0].strengths == "Produce\nDairy"
    assert best_stores[0].weaknesses == "Meat"
    assert best_stores[0].run_id == run.id

    deals = db_session.query(Deal).all()
    assert len(deals) == 1
    assert deals[0].store_name == "Store A"
    assert deals[0].item_name == "Apple"
    assert deals[0].score == 9
    assert deals[0].run_id == run.id

@pytest.mark.asyncio
async def test_run_scrape_and_analyze_no_deals(mock_session_local, db_session, mock_manager, mock_analyzer):
    # Manager returns empty deals but has a failed scrape
    mock_manager.run_all_scrapers.return_value = ([], [{"store_name": "Store C", "error_message": "Network error"}])

    await run_scrape_and_analyze()

    # Analyzer should not be called
    mock_analyzer.analyze_deals.assert_not_called()

    # Verify DB
    runs = db_session.query(Run).all()
    assert len(runs) == 1

    fails = db_session.query(FailedScrape).all()
    assert len(fails) == 1
    assert fails[0].store_name == "Store C"

    # Should have no deals or best store
    assert len(db_session.query(Deal).all()) == 0
    assert len(db_session.query(BestStore).all()) == 0

@pytest.mark.asyncio
async def test_run_scrape_and_analyze_exception(mock_session_local, db_session, mock_manager, mock_analyzer):
    # Manager throws an exception
    mock_manager.run_all_scrapers.side_effect = Exception("Critical network failure")

    # Should not raise, just log the error and cleanup DB session
    await run_scrape_and_analyze()

    # Run should be created before exception
    runs = db_session.query(Run).all()
    assert len(runs) == 1

    # But no deals/fails since it crashed
    assert len(db_session.query(FailedScrape).all()) == 0
    assert len(db_session.query(Deal).all()) == 0
    assert len(db_session.query(BestStore).all()) == 0


@patch("app.scheduler.AsyncIOScheduler")
@patch("app.scheduler.CronTrigger")
def test_start_scheduler_default_schedule(mock_cron_trigger, mock_asyncio_scheduler):
    # Setup mocks
    mock_scheduler_instance = MagicMock()
    mock_asyncio_scheduler.return_value = mock_scheduler_instance
    mock_trigger_instance = MagicMock()
    mock_cron_trigger.from_crontab.return_value = mock_trigger_instance

    # Ensure no environment variable for SCRAPE_SCHEDULE
    if "SCRAPE_SCHEDULE" in os.environ:
        del os.environ["SCRAPE_SCHEDULE"]

    # Call the function
    scheduler = start_scheduler()

    # Assertions
    mock_asyncio_scheduler.assert_called_once()
    mock_cron_trigger.from_crontab.assert_called_once_with("0 2 * * 1,4")
    mock_scheduler_instance.add_job.assert_called_once_with(
        run_scrape_and_analyze,
        mock_trigger_instance
    )
    mock_scheduler_instance.start.assert_called_once()
    assert scheduler == mock_scheduler_instance

@patch("app.scheduler.AsyncIOScheduler")
@patch("app.scheduler.CronTrigger")
def test_start_scheduler_custom_schedule(mock_cron_trigger, mock_asyncio_scheduler):
    # Setup mocks
    mock_scheduler_instance = MagicMock()
    mock_asyncio_scheduler.return_value = mock_scheduler_instance
    mock_trigger_instance = MagicMock()
    mock_cron_trigger.from_crontab.return_value = mock_trigger_instance

    # Set custom environment variable
    custom_cron = "0 12 * * *"
    with patch.dict(os.environ, {"SCRAPE_SCHEDULE": custom_cron}):
        # Call the function
        scheduler = start_scheduler()

    # Assertions
    mock_asyncio_scheduler.assert_called_once()
    mock_cron_trigger.from_crontab.assert_called_once_with(custom_cron)
    mock_scheduler_instance.add_job.assert_called_once_with(
        run_scrape_and_analyze,
        mock_trigger_instance
    )
    mock_scheduler_instance.start.assert_called_once()
    assert scheduler == mock_scheduler_instance
