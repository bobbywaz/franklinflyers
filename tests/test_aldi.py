from unittest.mock import AsyncMock, patch

import pytest

from app.scrapers.aldi import AldiScraper


class DummyLocator:
    def __init__(self):
        self.wait_for = AsyncMock()
        self.fill = AsyncMock()
        self.click = AsyncMock()
        self.screenshot = AsyncMock()
        self.first = self


class DummyFrame:
    def __init__(self):
        self.placeholder_locator = DummyLocator()
        self.find_stores_button = DummyLocator()
        self.select_button = DummyLocator()
        self.greenfield_result = DummyLocator()
        self.selected_marker = DummyLocator()
        self.canvas_locator = DummyLocator()

    def get_by_placeholder(self, value):
        assert value == "Enter your ZIP Code"
        return self.placeholder_locator

    def get_by_role(self, role, name):
        assert role == "button"
        if name == "Find Stores":
            return self.find_stores_button
        if name == "Select":
            return self.select_button
        raise AssertionError(f"Unexpected button requested: {name}")

    def locator(self, value):
        if value == "text=Aldi, Greenfield":
            return self.greenfield_result
        if value == "text=Selected":
            return self.selected_marker
        if value == "canvas":
            return self.canvas_locator
        raise AssertionError(f"Unexpected locator requested: {value}")


class DummyPage:
    def __init__(self, cookie_button, info_frame, main_frame):
        self.set_viewport_size = AsyncMock()
        self.goto = AsyncMock()
        self.wait_for_timeout = AsyncMock()
        self.screenshot = AsyncMock()
        self._cookie_button = cookie_button
        self._info_frame = info_frame
        self._main_frame = main_frame

    def get_by_role(self, role, name):
        assert role == "button"
        assert name == "Accept All"
        return self._cookie_button

    def frame_locator(self, selector):
        if selector == 'iframe[title="Information Panel"]':
            return self._info_frame
        if selector == 'iframe[title="Main Panel"]':
            return self._main_frame
        raise AssertionError(f"Unexpected frame requested: {selector}")


@pytest.mark.asyncio
@patch("app.scrapers.aldi.logger")
async def test_aldi_scrape_selects_zip_in_iframe_before_screenshot(mock_logger):
    scraper = AldiScraper()
    cookie_button = DummyLocator()
    info_frame = DummyFrame()
    main_frame = DummyFrame()
    mock_page = DummyPage(cookie_button, info_frame, main_frame)
    scraper._analyze_screenshot_with_gemini = AsyncMock(
        return_value={
            "flyer_start_date": "2026-04-30",
            "flyer_end_date": "2026-05-06",
            "deals": [
                {"name": "Strawberries", "price": "$1.99", "description": "1 lb pkg"},
                {"name": "Chicken Breasts", "price": "$2.29/lb", "description": "Family Pack"},
            ],
        }
    )

    result = await scraper.scrape(mock_page)

    assert result["scraper_key"] == "aldi"
    assert result["store_name"] == "ALDI"
    assert len(result["deals"]) == 2
    assert result["deals"][0]["name"] == "Strawberries"

    mock_page.set_viewport_size.assert_awaited_once_with({"width": 1600, "height": 2400})
    mock_page.goto.assert_awaited_once_with(
        "https://info.aldi.us/weekly-specials/weekly-ads?zipCode=01376",
        wait_until="domcontentloaded",
        timeout=60000,
    )
    cookie_button.click.assert_awaited_once_with(timeout=5000)
    info_frame.placeholder_locator.wait_for.assert_awaited_once_with(timeout=15000)
    info_frame.placeholder_locator.fill.assert_awaited_once_with("01376")
    info_frame.find_stores_button.click.assert_awaited_once_with()
    info_frame.greenfield_result.wait_for.assert_awaited_once_with(timeout=15000)
    info_frame.select_button.click.assert_awaited_once_with()
    main_frame.selected_marker.wait_for.assert_awaited_once_with(timeout=20000)
    main_frame.canvas_locator.wait_for.assert_awaited_once_with(state="visible", timeout=30000)
    main_frame.canvas_locator.screenshot.assert_awaited_once_with(path="/tmp/aldi_flyer.png")
    scraper._analyze_screenshot_with_gemini.assert_awaited_once_with("/tmp/aldi_flyer.png")
    mock_logger.error.assert_not_called()
