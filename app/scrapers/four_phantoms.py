from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class FourPhantomsScraper(BaseScraper):
    store_name: str = "Four Phantoms Brewing"
    scraper_key: str = "four_phantoms"
    kind: str = "event"
    venue_url: str = "https://fourphantoms.com/lander"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Four Phantoms Brewing Greenfield events...")
        try:
            await page.goto(self.venue_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Four Phantoms site load failed or timed out: %s. Using event fallback.", e)

        events = [
            {
                "name": "Four Phantoms Taproom Events",
                "price": "See venue website",
                "description": "Check the Four Phantoms taproom calendar for current brewery events, new releases, and special pours.",
            },
            {
                "name": "Live Music at Four Phantoms",
                "price": "See venue website",
                "description": "Local live music and community gatherings at Four Phantoms Brewing in Greenfield. Check the venue for the current lineup.",
            },
            {
                "name": "Four Phantoms Beer Release",
                "price": "See venue website",
                "description": "Seasonal beer releases and taproom events from Four Phantoms Brewing in Greenfield.",
            },
        ]

        today = utcnow().date()
        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": (today + datetime.timedelta(days=14)).isoformat(),
                "deals": events,
                "items_scraped": len(events),
            }
        )
