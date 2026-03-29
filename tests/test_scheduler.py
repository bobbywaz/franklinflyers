import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.scheduler import run_scrape_and_analyze

@pytest.mark.asyncio
async def test_scheduler_error_handling_in_db_job():
    """
    Test that if ScraperManager throws an exception during run_scrape_and_analyze,
    the generic Exception block is caught and db.close is still called.
    """
    with patch('app.scheduler.SessionLocal') as mock_session_local, \
         patch('app.scheduler.ScraperManager') as mock_scraper_manager, \
         patch('app.scheduler.GeminiAnalyzer') as mock_gemini_analyzer, \
         patch('app.scheduler.Run') as mock_run:

        # Setup the db mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Setup the manager mock to raise an exception
        mock_manager_instance = MagicMock()
        mock_manager_instance.run_all_scrapers = AsyncMock(side_effect=Exception("Test exception from scraper manager"))
        mock_scraper_manager.return_value = mock_manager_instance

        # Call the function
        await run_scrape_and_analyze()

        # Verify that run_all_scrapers was called
        mock_manager_instance.run_all_scrapers.assert_called_once()

        # Verify that db.close() was called even though an exception was raised
        mock_db.close.assert_called_once()
