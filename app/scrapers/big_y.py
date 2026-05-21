import datetime
import logging
import re
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page

import httpx

from .base import BaseScraper
from .flipp_utils import extract_deals_from_overlay_labels, extract_flyer_dates

logger = logging.getLogger(__name__)


class BigYScraper(BaseScraper):
    store_name: str = "Big Y"
    scraper_key: str = "big_y"
    target_zip_code: str = "01376"
    store_locator_url: str = "https://www.bigy.com/store-locator"
    weekly_ad_url: str = "https://www.bigy.com/weeklyad/flyerview"
    flaresolverr_url: str = "http://172.20.0.1:8191/v1"
    tenant_id: str = "10008"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Navigating to %s Greenfield weekly ad...", self.store_name)

        scrape_page = page
        owned_page: Optional[Page] = None
        try:
            browser = getattr(page.context, "browser", None)
            if browser is not None:
                owned_page = await browser.new_page()
                scrape_page = owned_page

            await scrape_page.set_viewport_size({"width": 1600, "height": 2200})
            cookies, user_agent = await self._get_flaresolverr_cookies(self.store_locator_url)
            if cookies:
                await scrape_page.context.add_cookies(cookies)
            if user_agent:
                await scrape_page.set_extra_http_headers({"User-Agent": user_agent})

            updated_cookies = await self._select_greenfield_store(cookies, user_agent)
            if not updated_cookies:
                return None
            await scrape_page.context.add_cookies(updated_cookies)
            if not await self._prime_greenfield_browser_context(scrape_page):
                return None

            await scrape_page.goto(self.weekly_ad_url, wait_until="commit", timeout=60000)
            await scrape_page.wait_for_timeout(12000)

            main_frame = scrape_page.frame_locator('iframe[title="Main Panel"]')
            item_overlays = main_frame.locator("button.item-overlay")
            overlay_count = 0
            for _ in range(10):
                overlay_count = await item_overlays.count()
                if overlay_count > 0:
                    break
                await scrape_page.wait_for_timeout(3000)
            if overlay_count == 0:
                logger.error("Big Y flyer frame loaded, but no overlay items were present")
                return None

            main_text = await main_frame.locator("body").inner_text()
            overlay_labels = await item_overlays.evaluate_all(
                "(els) => els.map((el) => el.getAttribute('aria-label') || '').filter(Boolean)"
            )

            deals = extract_deals_from_overlay_labels(overlay_labels)
            if not deals:
                logger.error("Big Y flyer loaded, but no item overlays were readable")
                return None

            flyer_start, flyer_end = extract_flyer_dates(main_text)
            payload = {
                "items_scraped": len(overlay_labels),
                "flyer_start_date": flyer_start.isoformat() if flyer_start else None,
                "flyer_end_date": flyer_end.isoformat() if flyer_end else None,
                "deals": deals,
            }
            logger.info(
                "Extracted %s Big Y deals directly from %s readable flyer items",
                len(deals),
                len(overlay_labels),
            )
            return self.build_result(payload)
        except Exception as e:
            logger.error("Error scraping Big Y: %s", e)
            return None
        finally:
            if owned_page is not None:
                await owned_page.close()

    async def _get_flaresolverr_cookies(self, url: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
        logger.info("Requesting cookies from FlareSolverr for Big Y...")
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
        }
        try:
            async with httpx.AsyncClient(timeout=75.0) as client:
                resp = await client.post(self.flaresolverr_url, json=payload)
                response = resp.json()
                if response.get("status") == "ok":
                    solution = response.get("solution", {})
                    return solution.get("cookies"), solution.get("userAgent")
                logger.warning("FlareSolverr returned status %s for Big Y", response.get("status"))
        except Exception as e:
            logger.warning("FlareSolverr request failed for Big Y: %s", e)
        return None, None

    async def _select_greenfield_store(self, cookies: Optional[List[Dict]], user_agent: Optional[str]) -> Optional[List[Dict]]:
        logger.info("Selecting Big Y store context with ZIP %s before scraping...", self.target_zip_code)

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                client.headers.update({"Content-Type": "application/json", "x-tenant-id": self.tenant_id})
                if user_agent:
                    client.headers["User-Agent"] = user_agent
                if cookies:
                    for c in cookies:
                        client.cookies.set(c["name"], c["value"], domain=c.get("domain", ".bigy.com"))

                # 1. Resolve store
                resp = await client.post("https://www.bigy.com/api/store/search", json={"keyword": self.target_zip_code, "latitude": "", "longitude": ""})
                resp.raise_for_status()
                stores = resp.json()
                greenfield_store = next((s for s in stores if "Greenfield" in (s.get("Name") or "")), stores[0] if stores else None)

                if not greenfield_store:
                    logger.error("Big Y Greenfield search result did not appear for ZIP %s", self.target_zip_code)
                    return None

                # 2. Activate store
                payload = {"StoreID": greenfield_store.get("StoreId"), "StoreZipCode": greenfield_store.get("ZipCode"), "StoreCode": greenfield_store.get("StoreCode"), "ShopPath": "groceries"}
                resp = await client.put("https://www.bigy.com/api/store/update-guest-store", json=payload)
                resp.raise_for_status()

                # 3. Convert cookies back for Playwright
                pw_cookies = []
                for name, value in client.cookies.items():
                    pw_cookies.append({"name": name, "value": value, "domain": ".bigy.com", "path": "/"})
                return pw_cookies

        except Exception as e:
            logger.error("Failed to select Big Y store context for ZIP %s: %s", self.target_zip_code, e)
            return None

    async def _prime_greenfield_browser_context(self, page: Page) -> bool:
        try:
            await page.goto(self.store_locator_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
            shop_here = page.get_by_role("button", name="Shop Here").first
            await shop_here.click()
            await page.wait_for_timeout(4000)
            return True
        except Exception as e:
            logger.error("Big Y browser store priming failed after guest-store update: %s", e)
            return False
