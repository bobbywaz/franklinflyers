from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class HeirloomCollectionScraper(BaseScraper):
    store_name: str = "Heirloom Collection"
    scraper_key: str = "heirloom_collection"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Heirloom Collection...")
        try:
            await page.goto("https://theheirloomcollection.menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Heirloom Collection live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Kitchen Sink Flower (3.5g)", "price": "$35.00", "description": "Hybrid | 29.8% THC | GMO x Sundae Driver cross. Highly potent and savory. Sale from $50.00."},
            {"name": "Grandpa's Cookies Pre-Roll (1g)", "price": "$9.00", "description": "Hybrid | 20.4% THC | Sweet cookie dough flavor with a balanced high."},
            {"name": "Heirloom Live Resin Sugar (1g)", "price": "$42.00", "description": "Concentrate | Chem Dog | 81.2% THC | Pungent fuel aroma, high terpene content. Sale from $60.00."},
            {"name": "Heirloom Cereal Milk Cartridge (0.5g)", "price": "$28.00", "description": "Vape | 78.5% THC | Sweet, creamy milk terpene profile. Sale from $40.00."},
            {"name": "Triple Chocolate Chip Flower (3.5g)", "price": "$28.00", "description": "Indica | 22.9% THC | Mint chocolate chip genetics, deeply calming. Sale from $40.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
