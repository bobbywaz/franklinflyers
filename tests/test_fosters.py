from unittest.mock import AsyncMock, patch, MagicMock
import os
import pytest
from app.scrapers.fosters import FostersScraper


@pytest.mark.asyncio
async def test_fosters_extract_deals_from_pdf_if_available():
    scraper = FostersScraper()
    pdf_path = "/tmp/real_fosters_flyer.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Test flyer PDF not found on host /tmp")

    result = scraper._extract_deals_from_pdf(pdf_path, pdf_url="https://fosterssupermarketdata.shoptocook.com/shoptocook/Content/CircularPDF/01139/Fosters_091426_LR.pdf")
    assert result is not None
    assert "deals" in result
    assert len(result["deals"]) >= 10
    assert result["flyer_start_date"] == "2026-09-14"
    assert result["flyer_end_date"] == "2026-09-19"
    assert any("Steak" in d["name"] or "Chicken" in d["name"] for d in result["deals"])


@pytest.mark.asyncio
@patch("builtins.open", new_callable=MagicMock)
@patch("app.scrapers.fosters.httpx.AsyncClient")
async def test_fosters_scrape_uses_local_pdf_extraction(mock_httpx, mock_open):
    scraper = FostersScraper()
    dummy_page = AsyncMock()
    mock_link = AsyncMock()
    mock_link.get_attribute.return_value = "https://example.com/Fosters_091426_LR.pdf"
    dummy_page.query_selector.return_value = mock_link

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF-1.6\n%%EOF"
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_httpx.return_value.__aenter__.return_value = mock_client

    with patch.object(scraper, "_extract_deals_from_pdf") as mock_extract:
        mock_extract.return_value = {
            "flyer_start_date": "2026-09-14",
            "flyer_end_date": "2026-09-19",
            "items_scraped": 2,
            "deals": [
                {"name": "Porterhouse Steak", "price": "$12.99/Lb.", "description": "USDA Choice"},
                {"name": "Green Beans", "price": "$2.99/Lb.", "description": "Fresh"},
            ],
        }

        result = await scraper.scrape(dummy_page)
        assert result is not None
        assert result["scraper_key"] == "fosters"
        assert result["kind"] == "grocery"
        assert len(result["deals"]) == 2
        assert result["deals"][0]["name"] == "Porterhouse Steak"
        assert str(result["flyer_start_date"]) == "2026-09-14"
