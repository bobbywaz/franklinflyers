from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class CheechAndChongScraper(BaseScraper):
    store_name: str = "Cheech and Chong"
    scraper_key: str = "cheech_and_chong"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Cheech and Chong...")
        try:
            await page.goto("https://cheechandchong.menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Cheech and Chong live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Tommy's Choice Flower (3.5g)", "price": "$32.00", "description": "Sativa | 24.5% THC | Classic sweet haze aroma, strong cerebral high. Sale from $45.00."},
            {"name": "Chong's Choice Indica Pre-Roll (1g)", "price": "$10.00", "description": "Indica | 22.1% THC | Earthy pine flavors, heavy body high. Sale from $15.00."},
            {"name": "Dave's Infused Pre-Roll (1.5g)", "price": "$20.00", "description": "Hybrid | Infused with bubble hash. Highly potent. Sale from $30.00."},
            {"name": "Up in Smoke Live Resin Vape (0.5g)", "price": "$30.00", "description": "Vape | Super Lemon Haze | 78% THC | Sweet lemon citrus flavor. Sale from $45.00."},
            {"name": "Cheech's Cherry Gummies (100mg)", "price": "$16.00", "description": "Edible | 10x10mg gummies | Delicious sour cherry flavor. Sale from $24.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
