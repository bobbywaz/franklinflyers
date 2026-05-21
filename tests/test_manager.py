from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.manager import ScraperManager


@pytest.mark.asyncio
async def test_run_single_returns_keyed_success_result():
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_async_playwright_cm = MagicMock()
    mock_async_playwright_cm.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_async_playwright_cm.__aexit__ = AsyncMock(return_value=None)

    payload = {
        "scraper_key": "aldi",
        "store_name": "ALDI",
        "kind": "grocery",
        "items_scraped_count": 42,
        "deals": [{"name": "deal1", "price": "1.00", "description": "desc"}],
    }

    with patch("app.manager.async_playwright", return_value=mock_async_playwright_cm):
        manager = ScraperManager()
        manager.registry = {"aldi": MagicMock(store_name="ALDI", scrape=AsyncMock(return_value=payload))}
        manager.scraper_order = ["aldi"]

        result = await manager.run_single("aldi")

    assert result["status"] == "success"
    assert result["scraper_key"] == "aldi"
    assert result["payload"]["item_count"] == 1
    assert result["payload"]["deal_count"] == 1
    assert result["payload"]["items_scraped_count"] == 42
    mock_browser.close.assert_called_once()


@pytest.mark.asyncio
async def test_run_full_batch_returns_success_and_failure_results():
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_playwright = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_async_playwright_cm = MagicMock()
    mock_async_playwright_cm.__aenter__ = AsyncMock(return_value=mock_playwright)
    mock_async_playwright_cm.__aexit__ = AsyncMock(return_value=None)

    good_scraper = MagicMock(
        store_name="Store1",
        scrape=AsyncMock(return_value={"scraper_key": "store1", "store_name": "Store1", "kind": "grocery", "deals": [{"name": "deal1", "price": "1.00"}]}),
    )
    bad_scraper = MagicMock(store_name="Store2", scrape=AsyncMock(side_effect=Exception("Scraping failed")))

    with patch("app.manager.async_playwright", return_value=mock_async_playwright_cm):
        manager = ScraperManager()
        manager.registry = {"store1": good_scraper, "store2": bad_scraper}
        manager.scraper_order = ["store1", "store2"]

        results = await manager.run_full_batch()

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[0]["payload"]["item_count"] == 1
    assert results[0]["payload"]["items_scraped_count"] == 1
    assert results[1]["status"] == "failed"
    assert "Scraping failed" in results[1]["error_message"]
    assert mock_context.new_page.call_count == 2
    assert mock_browser.close.called
