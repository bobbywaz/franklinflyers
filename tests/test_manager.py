import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Mock missing dependencies
sys.modules['fastapi'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()

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

@pytest.fixture
def mock_gas_scraper():
    scraper = MagicMock()
    scraper.store_name = "Gas Prices"
    scraper.scrape = AsyncMock(return_value=[{"name": "gas1", "price": "3.50"}])
    return scraper

@pytest.mark.asyncio
async def test_run_all_scrapers(mock_scrapers, mock_gas_scraper):
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
        manager.gas_scraper = mock_gas_scraper

        all_deals, gas_prices, failed_scrapes = await manager.run_all_scrapers()

        assert len(all_deals) == 1
        assert all_deals[0]["name"] == "deal1"
        assert all_deals[0]["store_name"] == "Store1"

        assert len(gas_prices) == 1
        assert gas_prices[0]["name"] == "gas1"

        assert len(failed_scrapes) == 1
        assert failed_scrapes[0]["store_name"] == "Store2"
        assert "Scraping failed" in failed_scrapes[0]["error_message"]

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once()
        assert mock_context.new_page.call_count == 3
        assert mock_page.close.call_count == 2
        mock_browser.close.assert_called_once()
