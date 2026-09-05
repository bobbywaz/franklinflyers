from unittest.mock import AsyncMock, patch

import pytest

from app.scrapers.big_y import BigYScraper


class DummyLocator:
    def __init__(self, labels=None, inner_text=""):
        self.labels = labels or []
        self.inner_text_value = inner_text
        self.first = self
        self.wait_for = AsyncMock()
        self.count = AsyncMock(return_value=len(self.labels))
        self.click = AsyncMock()

    async def inner_text(self):
        return self.inner_text_value

    async def evaluate_all(self, _script):
        return self.labels


class DummyFrame:
    def __init__(self, body_text="", overlay_labels=None):
        self.body_locator = DummyLocator(inner_text=body_text)
        self.overlay_locator = DummyLocator(labels=overlay_labels or [])

    def locator(self, selector):
        if selector == "body":
            return self.body_locator
        if selector == "button.item-overlay":
            return self.overlay_locator
        raise AssertionError(f"Unexpected frame selector: {selector}")


class DummyContext:
    def __init__(self):
        self.add_cookies = AsyncMock()


class FakeBigYPage:
    def __init__(self, overlay_labels=None, selection_result=None):
        self.events = []
        self.context = DummyContext()
        self.url = "about:blank"
        self.selection_result = selection_result or {"success": True, "storeName": "Greenfield"}
        self.set_viewport_size = AsyncMock()
        self._shop_here = DummyLocator()
        self._main_frame = DummyFrame(
            body_text="More Publications\nWeekly Ad\nApr 30th - May 6th\nSelected",
            overlay_labels=overlay_labels or [],
        )

    async def goto(self, url, **kwargs):
        self.events.append(("goto", url))

    async def wait_for_timeout(self, milliseconds):
        self.events.append(("wait_for_timeout", milliseconds))

    async def set_extra_http_headers(self, headers):
        self.events.append(("headers", headers.get("User-Agent")))

    async def evaluate(self, _script, _args):
        return self.selection_result

    def get_by_role(self, role, name):
        if role == "button" and name == "Shop Here":
            return self._shop_here
        raise AssertionError(f"Unexpected role lookup: {(role, name)}")

    def frame_locator(self, selector):
        if selector == 'iframe[title="Main Panel"]':
            return self._main_frame
        raise AssertionError(f"Unexpected frame requested: {selector}")


@pytest.mark.asyncio
@patch("app.scrapers.big_y.logger")
async def test_big_y_scrape_extracts_items_from_flipp_overlay_text(mock_logger):
    scraper = BigYScraper()
    page = FakeBigYPage(
        overlay_labels=[
            "Food Club Butter, , $2.49 . Select for details.",
            "De Cecco Pasta, MIX OR MATCH, 2 for $4 . Select for details.",
            "Food Club Butter, , $2.49 . Select for details.",
        ]
    )
    scraper._get_flaresolverr_cookies = AsyncMock(
        return_value=([{"name": "cf_clearance", "value": "x", "domain": "www.bigy.com", "path": "/"}], "UnitTest-UA")
    )

    result = await scraper.scrape(page)

    assert result["store_name"] == "Big Y"
    assert result["scraper_key"] == "big_y"
    assert result["flyer_start_date"].isoformat() == "2026-04-30"
    assert result["flyer_end_date"].isoformat() == "2026-05-06"
    assert result["items_scraped_count"] == 3
    assert len(result["deals"]) == 2
    assert result["deals"][0]["name"] == "Food Club Butter"
    assert result["deals"][0]["price"] == "$2.49"
    assert result["deals"][1]["description"] == "MIX OR MATCH"

    assert page.context.add_cookies.await_count == 1
    page.set_viewport_size.assert_awaited_once_with({"width": 1600, "height": 2200})
    page._shop_here.click.assert_awaited_once()
    assert ("headers", "UnitTest-UA") in page.events
    assert ("goto", scraper.store_locator_url) in page.events
    assert ("goto", scraper.weekly_ad_url) in page.events
    mock_logger.error.assert_not_called()


@pytest.mark.asyncio
@patch("app.scrapers.big_y.logger")
async def test_big_y_scrape_returns_empty_when_store_selection_fails(mock_logger):
    scraper = BigYScraper()
    page = FakeBigYPage(selection_result={"success": False, "error": "store lookup failed"})
    scraper._get_flaresolverr_cookies = AsyncMock(return_value=(None, None))

    result = await scraper.scrape(page)

    assert result is None
    assert ("goto", scraper.weekly_ad_url) not in page.events
    mock_logger.error.assert_called()
