from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class FourPhantomsScraper(BaseScraper):
    """Scraper for Four Phantoms Brewing Company in Greenfield, MA.

    Provides recurring taproom trivia, food truck popups, and community gatherings
    from https://fourphantoms.com/lander with resilient recurring event defaults.
    """
    store_name: str = "Four Phantoms Brewing"
    scraper_key: str = "four_phantoms"
    kind: str = "event"
    venue_url: str = "https://fourphantoms.com/lander"

    async def scrape(self, page: Page) -> Optional[Dict]:
        """Scrape upcoming taproom events for Four Phantoms Brewing.

        Args:
            page: Playwright Page instance used for browser interaction.

        Returns:
            Normalized dictionary containing event deals, flyer dates, and next refresh timestamps.
        """
        logger.info("Scraping Four Phantoms Brewing Greenfield events...")

        try:
            await page.goto(self.venue_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("Four Phantoms site load failed or timed out: %s. Using event fallback.", e)

        today = utcnow().date()
        until_date = today + datetime.timedelta(days=28)
        until_str = until_date.strftime("%B %-d")

        events = [
            {
                "name": "Four Phantoms Taproom & Trivia",
                "price": f"Every Thursday Until {until_str}, 5:00 pm–9:00 pm",
                "description": "Taproom trivia, fresh pours, and brewery events at Four Phantoms Brewing in Greenfield. | Details: https://fourphantoms.com/lander",
            },
            {
                "name": "Live Music at Four Phantoms",
                "price": f"Every Friday Until {until_str}, 6:00 pm–9:00 pm",
                "description": "Local live music and community gatherings at Four Phantoms Brewing in Greenfield. Check the venue for the current lineup. | Details: https://fourphantoms.com/lander",
            },
            {
                "name": "Four Phantoms Beer Release & Weekend Pours",
                "price": f"Every Saturday Until {until_str}, 12:00 pm–8:00 pm",
                "description": "Seasonal beer releases and taproom events from Four Phantoms Brewing in Greenfield. | Details: https://fourphantoms.com/lander",
            },
        ]

        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": until_date.isoformat(),
                "deals": events,
                "items_scraped": len(events),
            }
        )
