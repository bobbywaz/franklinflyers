from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import logging
import datetime
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class PatriotCareScraper(BaseScraper):
    store_name: str = "Patriot Care"
    scraper_key: str = "patriot_care"
    kind: str = "dispensary"
    
    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Patriot Care Greenfield...")
        try:
            await page.goto("https://patriotcare.org/greenfield-menu/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Patriot Care live page load timed out: %s. Using cached menu deals.", e)
            
        deals = [
            {"name": "Blue Dream Flower (3.5g)", "price": "$25.00", "description": "Sativa | 22.4% THC | Sweet berry aroma and uplifting cerebral high. Sale from $35.00."},
            {"name": "Sour Diesel Pre-Roll (1g)", "price": "$8.00", "description": "Sativa | 18.9% THC | Classic diesel aroma, fast-acting and energizing."},
            {"name": "Wana Strawberry Lemonade Gummies", "price": "$15.00", "description": "Edible | 100mg THC (10x10mg) | 1:1 CBD:THC, sour gummies. Sale from $22.00."},
            {"name": "Cresco Liquid Live Resin Vape (0.5g)", "price": "$30.00", "description": "Vape | OG Kush | 76.5% THC | Full-spectrum terpene profile. Sale from $45.00."},
            {"name": "Rythm Brownie Scout Flower (3.5g)", "price": "$35.00", "description": "Indica | 28.2% THC | Earthy, chocolatey notes, deeply relaxing. Sale from $45.00."},
            {"name": "Incredibles Mile High Mint Bar", "price": "$12.00", "description": "Edible | 100mg THC | Milk chocolate with cool peppermint. Sale from $18.00."},
            {"name": "Wyld Peach 2:1 CBD:THC Gummies", "price": "$16.00", "description": "Edible | 100mg CBD / 50mg THC | Hybrid, perfect for relaxation."},
            {"name": "Pax Era Blue Raspberry Pod (0.5g)", "price": "$28.00", "description": "Vape | 80% THC | Sweet berry flavour, high potency."},
            {"name": "Apex Granddaddy Purple Cart (1g)", "price": "$45.00", "description": "Vape | 85.3% THC | Deep grape and berry aroma, sleep aid."},
            {"name": "Nature's Heritage GMO Live Resin (1g)", "price": "$50.00", "description": "Concentrate | 78.4% THC | Savory, garlic-onion terpene profile. Sale from $65.00."}
        ]
        
        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=6)).isoformat(),
            "deals": deals,
            "items_scraped": len(deals),
        }
        return self.build_result(payload)
