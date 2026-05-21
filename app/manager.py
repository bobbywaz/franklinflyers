import logging
import asyncio
from playwright.async_api import async_playwright
from .scrapers.aldi import AldiScraper
from .scrapers.big_y import BigYScraper
from .scrapers.food_city import FoodCityScraper
from .scrapers.stop_and_shop import StopAndShopScraper
from .scrapers.fosters import FostersScraper
from .scrapers.gas import GasScraper
from typing import List, Dict, Tuple, Optional

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

    async def run_all_scrapers(self, run_date: str = None, db_queue: Optional[asyncio.Queue] = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Run all registered scrapers using a task queue with retries and return:
        - List of all found deals
        - List of all gas prices
        - List of errors for failed scrapers
        """
        all_deals = []
        gas_prices = []
        failed_scrapes = []

        # Setup the queue
        queue = asyncio.Queue()

        # Add grocery scrapers to queue
        for scraper in self.scrapers:
            await queue.put({
                'type': 'grocery',
                'scraper': scraper,
                'attempt': 1,
                'max_attempts': 3
            })

        # Add gas scraper to queue
        await queue.put({
            'type': 'gas',
            'scraper': self.gas_scraper,
            'attempt': 1,
            'max_attempts': 3
        })

        async def worker(context):
            while not queue.empty():
                try:
                    task = await queue.get()
                    scraper_type = task['type']
                    scraper = task['scraper']
                    attempt = task['attempt']
                    max_attempts = task['max_attempts']
                    store_name = getattr(scraper, 'store_name', 'Gas Prices')

                    logger.info(f"Worker processing {store_name} (Attempt {attempt}/{max_attempts})")

                    try:
                        page = await context.new_page()

                        if scraper_type == 'grocery':
                            deals = await scraper.scrape(page)
                            if not deals:
                                raise ValueError("Scraper returned empty results")
                            # Add store name to each deal
                            for d in deals:
                                d['store_name'] = scraper.store_name
                            all_deals.extend(deals)
                        elif scraper_type == 'gas':
                            found_gas = await scraper.scrape(page, run_date=run_date)
                            if not found_gas:
                                raise ValueError("Gas scraper returned empty results")
                            gas_prices.extend(found_gas)
                            if db_queue:
                                for gp in found_gas:
                                    await db_queue.put({'type': 'gas_price', 'data': gp})

                        logger.info(f"Successfully scraped {store_name}")

                    except Exception as e:
                        logger.warning(f"Error scraping {store_name} on attempt {attempt}: {e}")
                        if attempt < max_attempts:
                            logger.info(f"Re-queuing {store_name} for attempt {attempt + 1}")
                            task['attempt'] += 1
                            await queue.put(task)
                        else:
                            logger.error(f"Failed to scrape {store_name} after {max_attempts} attempts.")
                            failed_item = {"store_name": store_name, "error_message": str(e)}
                            failed_scrapes.append(failed_item)
                            if db_queue:
                                await db_queue.put({'type': 'failed_scrape', 'data': failed_item})
                    finally:
                        await page.close()
                        queue.task_done()
                except asyncio.CancelledError:
                    break

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )

            # Create 3 concurrent workers
            num_workers = 3
            workers = [asyncio.create_task(worker(context)) for _ in range(num_workers)]

            # Wait for the queue to be fully processed
            await queue.join()

            # Cancel workers
            for w in workers:
                w.cancel()

            await asyncio.gather(*workers, return_exceptions=True)

            await browser.close()
        
        return all_deals, gas_prices, failed_scrapes
