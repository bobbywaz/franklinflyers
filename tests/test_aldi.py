import pytest
from unittest.mock import AsyncMock, patch
from app.scrapers.aldi import AldiScraper

@pytest.mark.asyncio
@patch("app.scrapers.aldi.logger")
async def test_aldi_scrape(mock_logger):
    scraper = AldiScraper()
    mock_page = AsyncMock()

    items = await scraper.scrape(mock_page)

    # Verify logging
    mock_logger.info.assert_called_once_with("Navigating to ALDI weekly ad...")

    # Verify playwright page interactions
    mock_page.goto.assert_called_once_with("https://www.aldi.us/weekly-specials/our-weekly-ads/")
    mock_page.wait_for_timeout.assert_called_once_with(3000)

    # Verify the current placeholder return value
    assert len(items) == 2
    assert items[0]["name"] == "Strawberries"
    assert items[0]["price"] == "$1.99"
    assert items[0]["description"] == "1 lb pkg"

    assert items[1]["name"] == "Chicken Breasts"
    assert items[1]["price"] == "$2.29/lb"
    assert items[1]["description"] == "Family Pack"
