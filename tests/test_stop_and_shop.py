import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scrapers.stop_and_shop import StopAndShopScraper


@pytest.fixture
def mock_httpx_response():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "items": [
            {
                "name": "Stop & Shop Chicken Leg Quarters",
                "current_price": 0.79,
                "post_price_text": "/lb.",
                "merchant_name": "Stop & Shop",
                "valid_from": "2026-04-24T04:00:00+00:00",
                "valid_to": "2026-05-01T03:59:59+00:00",
            },
            {
                "name": "CareOne Vitamins",
                "sale_story": "BUY 1 GET 1 FREE Of Equal or Lesser Value",
                "merchant_name": "Stop & Shop",
                "valid_from": "2026-04-25T04:00:00+00:00",
                "valid_to": "2026-05-02T03:59:59+00:00",
            },
            {
                "name": "CareOne Vitamins",
                "sale_story": "BUY 1 GET 1 FREE Of Equal or Lesser Value",
                "merchant_name": "Stop & Shop",
                "valid_from": "2026-04-25T04:00:00+00:00",
                "valid_to": "2026-05-02T03:59:59+00:00",
            },
            {
                "name": "Ignore Me",
                "current_price": 9.99,
                "merchant_name": "Different Store",
                "valid_from": "2026-04-25T04:00:00+00:00",
                "valid_to": "2026-05-02T03:59:59+00:00",
            },
        ]
    }
    return response


@pytest.mark.asyncio
@patch("app.scrapers.stop_and_shop.httpx.AsyncClient")
@patch("app.scrapers.stop_and_shop.logger")
async def test_stop_and_shop_scrape_extracts_items_from_flipp_api(mock_logger, mock_async_client, mock_httpx_response):
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_httpx_response
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance

    scraper = StopAndShopScraper()
    dummy_page = AsyncMock()

    result = await scraper.scrape(dummy_page)

    assert result is not None
    assert result["store_name"] == "Stop & Shop"
    assert result["scraper_key"] == "stop_and_shop"
    assert result["items_scraped_count"] == 3
    assert len(result["deals"]) == 2

    assert result["flyer_start_date"] == datetime.date(2026, 4, 24)
    assert result["flyer_end_date"] == datetime.date(2026, 5, 2)

    assert result["deals"][0]["name"] == "Stop & Shop Chicken Leg Quarters"
    assert result["deals"][0]["price"] == "$0.79 /lb."
    assert result["deals"][1]["name"] == "CareOne Vitamins"
    assert result["deals"][1]["price"] == "BUY 1 GET 1 FREE Of Equal or Lesser Value"

    mock_client_instance.get.assert_awaited_once()
    mock_logger.error.assert_not_called()


@pytest.mark.asyncio
@patch("app.scrapers.stop_and_shop.httpx.AsyncClient")
@patch("app.scrapers.stop_and_shop.logger")
async def test_stop_and_shop_scrape_handles_empty_response(mock_logger, mock_async_client):
    empty_response = MagicMock()
    empty_response.raise_for_status = MagicMock()
    empty_response.json.return_value = {"items": []}

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = empty_response
    mock_async_client.return_value.__aenter__.return_value = mock_client_instance

    scraper = StopAndShopScraper()
    dummy_page = AsyncMock()

    result = await scraper.scrape(dummy_page)

    assert result is None
    mock_logger.error.assert_called_once_with("Stop & Shop Flipp API returned no items")
