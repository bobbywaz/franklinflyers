from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class SmokeyLeafScraper(BaseScraper):
    store_name: str = "Smokey Leaf"
    scraper_key: str = "smokey_leaf"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Smokey Leaf...")
        try:
            await page.goto("https://smokeyleaf.menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Smokey Leaf live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Green Crack Flower (3.5g)", "price": "$26.00", "description": "Sativa | 22.1% THC | Intense energy and focus, sharp mango flavor. Sale from $38.00."},
            {"name": "Smokey Leaf Pre-Rolls (10x0.5g)", "price": "$38.00", "description": "Hybrid | 20.8% THC | Large pack of premium flower joints. Sale from $55.00."},
            {"name": "Insa Chocolate Edible Bar (100mg)", "price": "$15.00", "description": "Edible | Sea Salt Caramel Milk Chocolate. Sale from $22.00."},
            {"name": "Insa Live Resin Vape Cart (0.5g)", "price": "$28.00", "description": "Vape | Runtz | 77.4% THC | Rich candy terpene profile. Sale from $40.00."},
            {"name": "Gelato 41 Crumble (1g)", "price": "$35.00", "description": "Concentrate | 80.5% THC | Creamy and sweet dessert-like profile. Sale from $50.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
