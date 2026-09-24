import pytest
import unittest.mock
from app.scrapers.base import BaseScraper

def test_base_scraper_abstract():
    # Test that BaseScraper cannot be instantiated directly
    with pytest.raises(TypeError) as excinfo:
        BaseScraper()
    assert "Can't instantiate abstract class BaseScraper" in str(excinfo.value)

def test_missing_scrape_method():
    # Test that a subclass missing the scrape method cannot be instantiated
    class InvalidScraper(BaseScraper):
        pass

    with pytest.raises(TypeError) as excinfo:
        InvalidScraper()
    assert "Can't instantiate abstract class InvalidScraper" in str(excinfo.value)

def test_valid_scraper_and_build_result():
    # Test that a valid subclass can be instantiated
    class ValidScraper(BaseScraper):
        store_name = "Test Store"
        scraper_key = "test_key"
        kind = "test_kind"

        async def scrape(self, page):
            return {"deals": [{"item": "Apple", "price": 1.0}]}

    scraper = ValidScraper()
    assert scraper.store_name == "Test Store"
    assert scraper.scraper_key == "test_key"
    assert scraper.kind == "test_kind"

    payload = {"deals": [{"item": "Apple", "price": 1.0}]}
    result = scraper.build_result(payload)

    assert result["scraper_key"] == "test_key"
    assert result["store_name"] == "Test Store"
    assert result["kind"] == "test_kind"
    assert "deals" in result
    assert result["deals"] == payload["deals"]
    assert "scraped_at" in result
    assert "expires_at" in result
    assert "next_refresh_at" in result
