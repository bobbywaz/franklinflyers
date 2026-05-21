from unittest.mock import AsyncMock, MagicMock, patch
import pytest
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
        manager.gas_scraper.flaresolverr_url = "http://127.0.0.1:1" # Invalid port to fail fast

        # Also mock httpx client to avoid 70s timeout
        with patch('httpx.AsyncClient.post', side_effect=Exception("Fast fail")):
            all_deals, gas_prices, failed_scrapes = await manager.run_all_scrapers()

        assert len(all_deals) == 1
        assert all_deals[0]["name"] == "deal1"
        assert all_deals[0]["store_name"] == "Store1"

        assert len(failed_scrapes) == 1
        assert failed_scrapes[0]["store_name"] == "Store2"
        assert "Scraping failed" in failed_scrapes[0]["error_message"]

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once()
        assert mock_context.new_page.call_count == 3
        assert mock_page.close.call_count == 2
        mock_browser.close.assert_called_once()
