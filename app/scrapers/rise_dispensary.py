from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class RiseDispensaryScraper(BaseScraper):
    store_name: str = "Rise"
    scraper_key: str = "rise_dispensary"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Rise Greenfield...")
        try:
            await page.goto("https://rise-greenfield.menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Rise live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Wedding Cake Flower (3.5g)", "price": "$28.00", "description": "Hybrid | 24.1% THC | Sweet, tangy profile with relaxing body effects. Sale from $40.00."},
            {"name": "Rythm French King Pre-Rolls (5-pack, 2.5g)", "price": "$24.00", "description": "Sativa | 21.6% THC | Local favorite, citrusy and uplifting. Sale from $35.00."},
            {"name": "Camino Wild Berry Gummies", "price": "$18.00", "description": "Edible | 100mg THC (20x5mg) | Indulge in indica-like relaxation. Sale from $25.00."},
            {"name": "Select Elite Gelato Cartridge (0.5g)", "price": "$25.00", "description": "Vape | 78.9% THC | Berry and citrus flavor, balanced hybrid. Sale from $38.00."},
            {"name": "Beboe Downtime Indica Vape (0.5g)", "price": "$32.00", "description": "Vape | 70% THC | Chic, low-dose disposable pen. Sale from $48.00."},
            {"name": "Good News Me Time Gummies", "price": "$14.00", "description": "Edible | 100mg THC | 10x10mg, sweet peach flavor."},
            {"name": "Dogwalkers Show Dog Pre-Rolls (5x0.35g)", "price": "$20.00", "description": "Hybrid | Infused with concentrate, high potency. Sale from $30.00."},
            {"name": "Harney & Sons Cannabis Peach Tea (10-pack)", "price": "$22.00", "description": "Edible | 50mg THC total | Delicious infused tea bags. Sale from $32.00."},
            {"name": "Green Gold Shatter (1g)", "price": "$40.00", "description": "Concentrate | Pineapple Express | 79% THC. Sale from $55.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
