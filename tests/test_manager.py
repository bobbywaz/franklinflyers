from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import sys

mock_playwright = MagicMock()
sys.modules['playwright'] = mock_playwright
sys.modules['playwright.async_api'] = mock_playwright

from app.manager import ScraperManager

@pytest.fixture
def mock_scrapers():
    scraper1 = MagicMock()
    scraper1.store_name = "Store1"
    scraper1.scrape = AsyncMock(return_value=[{"name": "deal1", "price": "1.00"}])

    scraper2 = MagicMock()
    scraper2.store_name = "Store2"
    scraper2.scrape = AsyncMock(side_effect=Exception("Scraping failed"))

    return [scraper1, scraper2]

@pytest.mark.asyncio
async def test_run_all_scrapers(mock_scrapers):
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    # Mock async context manager for async_playwright()
    mock_async_playwright_cm = MagicMock()
    mock_async_playwright_cm.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_async_playwright_cm.__aexit__ = AsyncMock(return_value=None)

    with patch('app.manager.async_playwright', return_value=mock_async_playwright_cm):
        manager = ScraperManager()
        manager.scrapers = mock_scrapers
        manager.gas_scraper = MagicMock()
        manager.gas_scraper.store_name = "Gas Prices"
        manager.gas_scraper.scrape = AsyncMock(return_value=[{"station_name": "Test Gas"}])

        all_deals, gas_prices, failed_scrapes = await manager.run_all_scrapers()

        assert len(all_deals) == 1
        assert all_deals[0]["name"] == "deal1"
        assert all_deals[0]["store_name"] == "Store1"

        assert len(failed_scrapes) == 1
        assert failed_scrapes[0]["store_name"] == "Store2"
        assert "Scraping failed" in failed_scrapes[0]["error_message"]

        assert len(gas_prices) == 1
        assert gas_prices[0]["station_name"] == "Test Gas"

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once()

        # We now have 3 workers calling new_page for tasks
        assert mock_context.new_page.call_count >= 3
        mock_browser.close.assert_called_once()
