import datetime
import logging
import os
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
    flaresolverr_url: str = os.getenv("FLARESOLVERR_URL", "http://172.20.0.1:8191/v1")
    tenant_id: str = "10008"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Navigating to %s Greenfield weekly ad...", self.store_name)

        scrape_page = page
        owned_page: Optional[Page] = None
        owned_context = None
        try:
            cookies, user_agent = await self._get_flaresolverr_cookies(self.store_locator_url)

            browser = getattr(page.context, "browser", None)
            if browser is not None:
                context_args = {}
                if user_agent:
                    context_args["user_agent"] = user_agent
                owned_context = await browser.new_context(**context_args)
                if cookies:
                    await owned_context.add_cookies(cookies)
                owned_page = await owned_context.new_page()
                scrape_page = owned_page
            else:
                if cookies:
                    await scrape_page.context.add_cookies(cookies)
                if user_agent:
                    await scrape_page.set_extra_http_headers({"User-Agent": user_agent})

            await scrape_page.set_viewport_size({"width": 1600, "height": 2200})

            if not await self._select_greenfield_store_in_browser(scrape_page):
                return None
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
            if owned_context is not None:
                await owned_context.close()

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

    async def _select_greenfield_store_in_browser(self, page: Page) -> bool:
        logger.info("Selecting Big Y store context with ZIP %s in-browser...", self.target_zip_code)
        try:
            # We must be on the bigy.com domain to perform fetches and have cookies automatically managed
            if getattr(page, "url", "about:blank") == "about:blank":
                await page.goto(self.store_locator_url, wait_until="domcontentloaded", timeout=60000)

            result = await page.evaluate("""async ({zipCode, tenantId}) => {
                try {
                    // 1. Resolve store
                    const searchResp = await fetch("https://www.bigy.com/api/store/search", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "x-tenant-id": tenantId
                        },
                        body: JSON.stringify({keyword: zipCode, latitude: "", longitude: ""})
                    });
                    if (!searchResp.ok) {
                        throw new Error(`Search failed: ${searchResp.status} ${searchResp.statusText}`);
                    }
                    const stores = await searchResp.json();
                    const greenfieldStore = stores.find(s => (s.Name || "").includes("Greenfield")) || stores[0];
                    if (!greenfieldStore) {
                        throw new Error("No stores returned from search");
                    }

                    // 2. Activate store
                    const updateResp = await fetch("https://www.bigy.com/api/store/update-guest-store", {
                        method: "PUT",
                        headers: {
                            "Content-Type": "application/json",
                            "x-tenant-id": tenantId
                        },
                        body: JSON.stringify({
                            StoreID: greenfieldStore.StoreId,
                            StoreZipCode: greenfieldStore.ZipCode,
                            StoreCode: greenfieldStore.StoreCode,
                            ShopPath: "groceries"
                        })
                    });
                    if (!updateResp.ok) {
                        throw new Error(`Update guest store failed: ${updateResp.status} ${updateResp.statusText}`);
                    }
                    return { success: true, storeName: greenfieldStore.Name };
                } catch (e) {
                    return { success: false, error: e.message };
                }
            }""", {"zipCode": self.target_zip_code, "tenantId": self.tenant_id})

            if result.get("success"):
                logger.info("Successfully selected Big Y store context in-browser: %s", result.get("storeName"))
                return True
            else:
                logger.error("In-browser store selection failed: %s", result.get("error"))
                return False
        except Exception as e:
            logger.error("Failed to select Big Y store context in-browser for ZIP %s: %s", self.target_zip_code, e)
            return False

    async def _prime_greenfield_browser_context(self, page: Page) -> bool:
        try:
            await page.goto(self.store_locator_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
            shop_here = page.get_by_role("button", name="Shop Here").first
            try:
                await shop_here.click(timeout=10000)
                await page.wait_for_timeout(4000)
            except Exception:
                logger.info("Big Y store locator did not show Shop Here; continuing with the guest-store context")
            return True
        except Exception as e:
            logger.error("Big Y browser store priming failed after guest-store update: %s", e)
            return False
