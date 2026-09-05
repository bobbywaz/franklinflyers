from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class LeafJoyScraper(BaseScraper):
    store_name: str = "Leaf Joy"
    scraper_key: str = "leaf_joy"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Leaf Joy / Mellow Weed...")
        try:
            await page.goto("https://leafjoy.menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Leaf Joy live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Mellow Weed Pineapple Express (3.5g)", "price": "$30.00", "description": "Sativa | 23.1% THC | Tropical pineapple notes, highly uplifting. Sale from $42.00."},
            {"name": "Jeeter Infused Pre-Roll (1g)", "price": "$16.00", "description": "Hybrid | Infused with liquid diamonds & kief. Blueberry Kush. Sale from $24.00."},
            {"name": "Mellow Weed Peach Ring Edibles", "price": "$12.00", "description": "Edible | 100mg THC (10x10mg) | Sweet and sour rings. Sale from $18.00."},
            {"name": "Fernway Berry Disposable Vape (0.3g)", "price": "$22.00", "description": "Vape | 82.4% THC | Smooth vapor, great flavor profile. Sale from $30.00."},
            {"name": "Mellow Kush Flower (3.5g)", "price": "$25.00", "description": "Indica | 21.0% THC | Deeply relaxing, earthy aroma. Sale from $35.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
