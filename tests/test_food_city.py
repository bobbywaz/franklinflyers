from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.scrapers.food_city import FoodCityScraper


@pytest.mark.asyncio
@patch("builtins.open", new_callable=MagicMock)
@patch("app.scrapers.food_city.httpx.AsyncClient")
async def test_food_city_scrape_uses_gemini_when_available(mock_httpx, mock_open):
    scraper = FoodCityScraper()
    dummy_page = AsyncMock()
    mock_link = AsyncMock()
    mock_link.get_attribute.return_value = "https://www.foodcitymkt.com/s/FoodCity_091826_TurnersFalls_WEB.pdf"
    dummy_page.query_selector.return_value = mock_link

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF-1.6\n%%EOF"
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_httpx.return_value.__aenter__.return_value = mock_client

    with patch.object(scraper, "_analyze_pdf_with_gemini") as mock_gemini:
        mock_gemini.return_value = {
            "flyer_start_date": "2026-09-18",
            "flyer_end_date": "2026-09-24",
            "items_scraped": 2,
            "deals": [
                {"name": "Sirloin Steak", "price": "$6.99/lb", "description": "Boneless Beef"},
            ],
        }

        result = await scraper.scrape(dummy_page)
        assert result is not None
        assert result["scraper_key"] == "food_city"
        assert result["kind"] == "grocery"
        assert len(result["deals"]) == 1
        assert result["deals"][0]["name"] == "Sirloin Steak"
        assert str(result["flyer_start_date"]) == "2026-09-18"


@pytest.mark.asyncio
@patch("builtins.open", new_callable=MagicMock)
@patch("app.scrapers.food_city.httpx.AsyncClient")
async def test_food_city_scrape_falls_back_when_gemini_fails(mock_httpx, mock_open):
    scraper = FoodCityScraper()
    dummy_page = AsyncMock()
    mock_link = AsyncMock()
    mock_link.get_attribute.return_value = "https://www.foodcitymkt.com/s/FoodCity_091826_TurnersFalls_WEB.pdf"
    dummy_page.query_selector.return_value = mock_link

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF-1.6\n%%EOF"
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_httpx.return_value.__aenter__.return_value = mock_client

    # Simulate Gemini failure (e.g. 429 depleted credits)
    with patch.object(scraper, "_analyze_pdf_with_gemini", return_value=None):
        result = await scraper.scrape(dummy_page)
        assert result is not None
        assert result["scraper_key"] == "food_city"
        assert result["kind"] == "grocery"
        assert len(result["deals"]) > 10
        assert str(result["flyer_start_date"]) == "2026-09-18"
        assert str(result["flyer_end_date"]) == "2026-09-24"
        assert any("Steak" in d["name"] or "Chicken" in d["name"] for d in result["deals"])
