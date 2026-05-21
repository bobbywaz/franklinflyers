import pytest
from unittest.mock import AsyncMock, patch
from app.scrapers.aldi import AldiScraper

@pytest.mark.asyncio
@patch("app.scrapers.aldi.logger")
async def test_aldi_scrape(mock_logger):
    scraper = AldiScraper()
    mock_page = AsyncMock()

    items = await scraper.scrape(mock_page)

    # Verify logging for new structure
    # the first call is about navigating to ALDI
    mock_logger.info.assert_any_call("Navigating to ALDI Greenfield weekly ad...")

    # Verify playwright page interactions (with new wait_until mechanism)
    mock_page.goto.assert_called_once_with("https://info.aldi.us/weekly-specials/weekly-ads?zipCode=01301", wait_until="domcontentloaded", timeout=60000)
    mock_page.wait_for_timeout.assert_called_once_with(10000)
    mock_page.screenshot.assert_called_once_with(path="/tmp/aldi_flyer.png", full_page=False)

    # Since GEMINI_API_KEY is missing, it returns empty list
    assert items == []
