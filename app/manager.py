import logging
import asyncio
from playwright.async_api import async_playwright
from .scrapers.aldi import AldiScraper
from .scrapers.big_y import BigYScraper
from .scrapers.food_city import FoodCityScraper
from .scrapers.stop_and_shop import StopAndShopScraper
from .scrapers.fosters import FostersScraper
from .scrapers.gas import GasScraper
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self):
        self.scrapers = [
            AldiScraper(),
            BigYScraper(),
            FoodCityScraper(),
            StopAndShopScraper(),
            FostersScraper()
        ]
        self.gas_scraper = GasScraper()

    async def run_all_scrapers(self, run_date: str = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Run all registered scrapers and return:
        - List of all found deals
        - List of all gas prices
        - List of errors for failed scrapers
        """
        all_deals = []
        gas_prices = []
        failed_scrapes = []

        async def _scrape_grocery(scraper, context):
            try:
                page = await context.new_page()
                deals = await scraper.scrape(page)
                for d in deals:
                    d['store_name'] = scraper.store_name
                await page.close()
                return deals, None
            except Exception as e:
                logger.error(f"Scraper for {scraper.store_name} failed: {e}")
                return [], {"store_name": scraper.store_name, "error_message": str(e)}

        async def _scrape_gas(scraper, context, run_date):
            try:
                page = await context.new_page()
                found_gas = await scraper.scrape(page, run_date=run_date)
                await page.close()
                return found_gas, None
            except Exception as e:
                logger.error(f"Gas Scraper failed: {e}")
                return [], {"store_name": "Gas Prices", "error_message": str(e)}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )

            tasks = []
            for scraper in self.scrapers:
                tasks.append(_scrape_grocery(scraper, context))

            tasks.append(_scrape_gas(self.gas_scraper, context, run_date))

            results = await asyncio.gather(*tasks)

            grocery_results = results[:-1]
            gas_result = results[-1]

            for deals, error in grocery_results:
                if deals:
                    all_deals.extend(deals)
                if error:
                    failed_scrapes.append(error)

            if gas_result[0]:
                gas_prices.extend(gas_result[0])
            if gas_result[1]:
                failed_scrapes.append(gas_result[1])

            await browser.close()
        
        return all_deals, gas_prices, failed_scrapes
