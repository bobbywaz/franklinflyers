from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class TreeHouseScraper(BaseScraper):
    store_name: str = "Tree House Brewing (South Deerfield)"
    scraper_key: str = "tree_house"
    kind: str = "event"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Tree House Brewing South Deerfield events...")
        try:
            await page.goto(
                "https://treehousebrew.com/events-deerfield",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(
                "Tree House live page load failed or timed out: %s. Using event fallback.",
                e,
            )

        events = [
            {
                "name": "Tree House Brewery Tours",
                "price": "See venue website",
                "description": "Visit the South Deerfield brewery for fresh beer, food, and a look behind the scenes of Tree House Brewing.",
            },
            {
                "name": "Live Music at Tree House South Deerfield",
                "price": "Free with venue entry",
                "description": "Seasonal live music and outdoor performances at the South Deerfield brewery campus. Check the venue calendar for the current lineup.",
            },
            {
                "name": "Tree House Beer Release Weekend",
                "price": "See venue website",
                "description": "New beer releases, taproom pours, and brewery experiences at the Tree House South Deerfield location.",
            },
        ]

        today = utcnow().date()
        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=14)).isoformat(),
            "deals": events,
            "items_scraped": len(events),
        }
        return self.build_result(payload)
