import datetime
import logging
from typing import Dict, List, Optional, Tuple

import httpx
import requests
from playwright.async_api import Page

from .base import BaseScraper
from .flipp_utils import extract_deals_from_overlay_labels, extract_flyer_dates

logger = logging.getLogger(__name__)


class StopAndShopScraper(BaseScraper):
    store_name = "Stop & Shop"
    scraper_key = "stop_and_shop"
    postal_code = "01376"
    flipp_search_query = "Stop And Shop"
    flipp_search_url = "https://backflipp.wishabi.com/flipp/items/search"
    homepage_url = "https://stopandshop.com"
    weekly_ad_url = "https://stopandshop.com/weekly-ad?storeCode=0442"
    flaresolverr_url = "http://172.20.0.1:8191/v1"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Fetching %s weekly ad via Flipp API...", self.store_name)

        api_items = await self._fetch_flipp_api_items()
        # If we got items from the API, process them. Otherwise, try the fallback.
        if api_items and len(api_items) > 0:

            payload = self._build_flipp_api_payload(api_items)
            if not payload["deals"]:
                logger.error("Stop & Shop Flipp API returned no readable deals")
            else:
                logger.info(
                    "Extracted %s Stop & Shop deals directly from %s Flipp API items",
                    len(payload["deals"]),
                    len(api_items),
                )
                return self.build_result(payload)

        logger.info("Flipp API path failed or returned no items, falling back to browser extraction...")
        payload = await self._scrape_flipp_overlay(page)
        if payload is None:
            return None
        return self.build_result(payload)

    async def _fetch_flipp_api_items(self) -> Optional[List[Dict]]:
        # Try multiple query variations to ensure we get a match
        queries = [self.flipp_search_query, "Stop & Shop", "Stop and Shop", "Stop & Shop - Greenfield"]
        items = []

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                for q in queries:
                    logger.info("Searching Flipp API for '%s' in %s...", q, self.postal_code)
                    params = {
                        "locale": "en-us",
                        "postal_code": self.postal_code,
                        "q": q,
                    }
                    response = await client.get(self.flipp_search_url, params=params)
                    response.raise_for_status()
                    search_results = response.json().get("items") or []
                    
                    # Filter for Stop & Shop specifically
                    filtered = [
                        item
                        for item in search_results
                        if "stop" in (item.get("merchant_name") or "").lower() and "shop" in (item.get("merchant_name") or "").lower()
                    ]
                    
                    if filtered:
                        logger.info("Flipp API found %d matches using query: '%s'", len(filtered), q)
                        items = filtered
                        break
            
            return items
        except Exception as e:
            logger.warning("Stop & Shop Flipp API request failed: %s", e)
            return None

    def _build_flipp_api_payload(self, items: List[Dict]) -> Dict:
        deals: List[Dict] = []
        seen = set()
        flyer_start: Optional[datetime.date] = None
        flyer_end: Optional[datetime.date] = None

        for item in items:
            start = self._parse_iso_date(item.get("valid_from"))
            end = self._parse_iso_date(item.get("valid_to"))
            if start and (flyer_start is None or start < flyer_start):
                flyer_start = start
            if end and (flyer_end is None or end > flyer_end):
                flyer_end = end

            name = (item.get("name") or "").strip()
            price = self._format_flipp_api_price(item)
            description = self._format_flipp_api_description(item)
            if not name or not price:
                continue

            key = (name.lower(), price.lower(), description.lower())
            if key in seen:
                continue
            seen.add(key)
            deals.append(
                {
                    "name": name,
                    "price": price,
                    "description": description,
                }
            )

        return {
            "items_scraped": len(items),
            "flyer_start_date": flyer_start.isoformat() if flyer_start else None,
            "flyer_end_date": flyer_end.isoformat() if flyer_end else None,
            "deals": deals,
        }

    def _format_flipp_api_price(self, item: Dict) -> str:
        current_price = item.get("current_price")
        if current_price not in (None, ""):
            price = f"${current_price}"
            suffix = str(item.get("post_price_text") or "").strip()
            if suffix:
                price = f"{price} {suffix}"
            return price
        return str(item.get("sale_story") or "").strip()

    def _format_flipp_api_description(self, item: Dict) -> str:
        parts = []
        description = str(item.get("description") or "").strip()
        sale_story = str(item.get("sale_story") or "").strip()
        if description:
            parts.append(description)
        if sale_story and item.get("current_price") not in (None, ""):
            parts.append(sale_story)
        return " ".join(parts).strip()

    def _parse_iso_date(self, value: Optional[str]) -> Optional[datetime.date]:
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(value).date()
        except ValueError:
            return None

    async def _scrape_flipp_overlay(self, page: Page) -> Optional[Dict]:
        logger.info("Navigating to %s Greenfield weekly ad via browser fallback...", self.store_name)

        scrape_page = page
        owned_page: Optional[Page] = None
        try:
            browser = getattr(page.context, "browser", None)
            if browser is not None:
                owned_page = await browser.new_page()
                scrape_page = owned_page

            await scrape_page.set_viewport_size({"width": 1600, "height": 2200})
            
            # Prime with homepage to establish session/cookies via FlareSolverr.
            # DataDome is often less aggressive on the homepage than the ad page.
            cookies, user_agent = await self._get_flaresolverr_cookies(self.homepage_url)
            if cookies:
                await scrape_page.context.add_cookies(cookies)
            if user_agent:
                await scrape_page.set_extra_http_headers({"User-Agent": user_agent})

            await scrape_page.goto(self.weekly_ad_url, wait_until="commit", timeout=60000)
            await scrape_page.wait_for_timeout(15000)

            main_frame = scrape_page.frame_locator('iframe[title="Main Panel"]')
            item_overlays = main_frame.locator("button.item-overlay")
            
            overlay_count = 0
            for _ in range(10):
                overlay_count = await item_overlays.count()
                if overlay_count > 0:
                    break
                await scrape_page.wait_for_timeout(3000)
                
            if overlay_count == 0:
                logger.error("Stop & Shop flyer frame loaded, but no overlay items were present")
                return None

            main_text = await main_frame.locator("body").inner_text()
            overlay_labels = await item_overlays.evaluate_all(
                "(els) => els.map((el) => el.getAttribute('aria-label') || '').filter(Boolean)"
            )

            deals = extract_deals_from_overlay_labels(overlay_labels)
            if not deals:
                logger.error("Stop & Shop flyer loaded, but no item overlays were readable")
                return None

            flyer_start, flyer_end = extract_flyer_dates(main_text)

            payload = {
                "items_scraped": len(overlay_labels),
                "flyer_start_date": flyer_start.isoformat() if flyer_start else None,
                "flyer_end_date": flyer_end.isoformat() if flyer_end else None,
                "deals": deals,
            }

            logger.info(
                "Extracted %s Stop & Shop deals directly from %s readable flyer items",
                len(deals),
                len(overlay_labels)
            )
            return payload

        except Exception as e:
            logger.error("Error scraping Stop & Shop: %s", e)
            return None
        finally:
            if owned_page is not None:
                await owned_page.close()

    async def _get_flaresolverr_cookies(self, url: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
        logger.info("Requesting cookies from FlareSolverr for %s...", url)
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(self.flaresolverr_url, json=payload)
                response = resp.json()
            if response.get("status") == "ok":
                solution = response.get("solution", {})
                return solution.get("cookies"), solution.get("userAgent")
            logger.warning("FlareSolverr returned status %s for Stop & Shop", response.get("status"))
        except Exception as e:
            logger.warning("FlareSolverr request failed for Stop & Shop: %s", e)
        return None, None
