import logging
from playwright.async_api import async_playwright
from .scrapers.aldi import AldiScraper
from .scrapers.big_y import BigYScraper
from .scrapers.food_city import FoodCityScraper
from .scrapers.stop_and_shop import StopAndShopScraper
from .scrapers.fosters import FostersScraper
from typing import List, Dict

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

    async def run_all_scrapers(self) -> List[Dict]:
        """
        Run all registered scrapers and return a list of all found deals.
        Also returns a list of errors for failed scrapers.
        """
        all_deals = []
        failed_scrapes = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )

            for scraper in self.scrapers:
                try:
                    page = await context.new_page()
                    deals = await scraper.scrape(page)
                    # Add store name to each deal
                    for d in deals:
                        d['store_name'] = scraper.store_name
                    all_deals.extend(deals)
                    await page.close()
                except Exception as e:
                    logger.error(f"Scraper for {scraper.store_name} failed: {e}")
                    failed_scrapes.append({"store_name": scraper.store_name, "error_message": str(e)})

            await browser.close()
        
        return all_deals, failed_scrapes
