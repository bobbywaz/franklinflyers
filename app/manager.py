import logging
from typing import Dict, List, Optional

from playwright.async_api import async_playwright

from .scrapers.aldi import AldiScraper
from .scrapers.big_y import BigYScraper
from .scrapers.food_city import FoodCityScraper
from .scrapers.fosters import FostersScraper
from .scrapers.gas import GasScraper
from .scrapers.stop_and_shop import StopAndShopScraper

logger = logging.getLogger(__name__)


class ScraperManager:
    def __init__(self):
        grocery_scrapers = [
            AldiScraper(),
            BigYScraper(),
            FoodCityScraper(),
            StopAndShopScraper(),
            FostersScraper(),
        ]
        gas_scraper = GasScraper()

        self.registry = {scraper.scraper_key: scraper for scraper in grocery_scrapers}
        self.registry[gas_scraper.scraper_key] = gas_scraper
        self.scraper_order = [scraper.scraper_key for scraper in grocery_scrapers] + [gas_scraper.scraper_key]

    def list_scrapers(self) -> List[Dict]:
        cards = [
            {
                "scraper_key": "full_run",
                "store_name": "Full Run",
                "kind": "batch",
            }
        ]
        for scraper_key in self.scraper_order:
            scraper = self.registry[scraper_key]
            cards.append(
                {
                    "scraper_key": scraper_key,
                    "store_name": scraper.store_name,
                    "kind": "gas" if scraper_key == "gas" else "grocery",
                }
            )
        return cards

    async def run_single(self, scraper_key: str, run_date: str = None) -> Dict:
        scraper = self.registry[scraper_key]
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            try:
                result = await self._execute_scraper(scraper_key, context, run_date=run_date)
            finally:
                await browser.close()
        return result

    async def run_full_batch(self, run_date: str = None) -> List[Dict]:
        results = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            try:
                for scraper_key in self.scraper_order:
                    results.append(await self._execute_scraper(scraper_key, context, run_date=run_date))
            finally:
                await browser.close()
        return results

    async def _execute_scraper(self, scraper_key: str, context, run_date: str = None) -> Dict:
        scraper = self.registry[scraper_key]
        page = await context.new_page()
        try:
            if scraper_key == "gas":
                payload = await scraper.scrape(page, run_date=run_date)
                deal_count = len(payload.get("prices", [])) if payload else 0
            else:
                payload = await scraper.scrape(page)
                deal_count = len(payload.get("deals", [])) if payload else 0

            if not payload or deal_count == 0:
                return {
                    "scraper_key": scraper_key,
                    "store_name": scraper.store_name,
                    "kind": "gas" if scraper_key == "gas" else "grocery",
                    "status": "failed",
                    "error_message": "No data returned",
                    "payload": None,
                }

            payload["item_count"] = deal_count
            payload["deal_count"] = deal_count
            payload["items_scraped_count"] = payload.get("items_scraped_count", deal_count)
            return {
                "scraper_key": scraper_key,
                "store_name": scraper.store_name,
                "kind": payload["kind"],
                "status": "success",
                "error_message": None,
                "payload": payload,
            }
        except Exception as e:
            logger.error("Scraper for %s failed: %s", scraper.store_name, e)
            return {
                "scraper_key": scraper_key,
                "store_name": scraper.store_name,
                "kind": "gas" if scraper_key == "gas" else "grocery",
                "status": "failed",
                "error_message": str(e),
                "payload": None,
            }
        finally:
            await page.close()
