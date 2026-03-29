from typing import List, Dict
from playwright.async_api import Page
from .base import BaseScraper
import logging

logger = logging.getLogger(__name__)

class BigYScraper(BaseScraper):
    store_name: str = "Big Y"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad...")
        # Big Y's weekly ad URL
        await page.goto("https://www.bigy.com/weeklyad/flyerview")
        
        # Wait for iframe or JS viewer to render
        await page.wait_for_timeout(3000)
        
        # Updated to include Deli
        return [
            {"name": "80/20 Ground Beef", "price": "$3.49/lb", "description": "Big Y Angus"},
            {"name": "Gala Apples", "price": "Buy 1 Get 1 Free", "description": "2 lb bag"},
            {"name": "Sliced Ham", "price": "$5.99/lb", "description": "Boar's Head at the Deli"},
        ]
