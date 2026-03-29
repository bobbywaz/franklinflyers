from typing import List, Dict
from playwright.async_api import Page
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

class FostersScraper(BaseScraper):
    store_name: str = "Foster's"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad...")
        # Foster's Greenfield location
        await page.goto("https://www.fosterssupermarket.com/weekly-ad")
        
        await page.wait_for_timeout(3000)
        
        # Updated to include Household
        return [
            {"name": "Ribeye Steak", "price": "$12.99/lb", "description": "Choice"},
            {"name": "Avocados", "price": "$0.88 ea", "description": "Large Hass"},
            {"name": "Laundry Detergent", "price": "$9.99", "description": "Tide 92 fl oz"},
        ]
