from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
import re
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class GreenfieldFarmersMarketScraper(BaseScraper):
    store_name: str = "Greenfield Farmers Market"
    scraper_key: str = "greenfield_farmers_market"
    kind: str = "event"
    market_url: str = "https://www.greenfieldfarmersmarket.com/"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Greenfield Farmers Market schedule...")
        try:
            await page.goto(self.market_url, wait_until="domcontentloaded", timeout=30000)
            page_text = await page.locator("body").inner_text()
        except Exception as e:
            logger.error("Greenfield Farmers Market page load failed: %s", e)
            return None

        schedule_match = re.search(
            r"every Saturday from (\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m).*?season runs ([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)\s*-\s*([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)",
            page_text,
            re.IGNORECASE | re.DOTALL,
        )
        if not schedule_match:
            logger.error("Could not find Greenfield Farmers Market schedule text")
            return None

        start_time, end_time, season_start_text, season_end_text = schedule_match.groups()
        today = utcnow().date()
        year = today.year
        season_start_text = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", season_start_text)
        season_end_text = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", season_end_text)
        season_start = datetime.datetime.strptime(
            f"{season_start_text} {year}", "%B %d %Y"
        ).date()
        season_end = datetime.datetime.strptime(
            f"{season_end_text} {year}", "%B %d %Y"
        ).date()
        first_date = max(today, season_start)
        events = []
        current = first_date
        while current <= min(season_end, today + datetime.timedelta(days=14)):
            if current.weekday() == 5:
                events.append(
                    {
                        "name": "Greenfield Farmers Market",
                        "price": f"{current.strftime('%A, %B %-d')} | {start_time}–{end_time}",
                        "description": "Court Square, Greenfield, MA | Local farmers, food producers, and artisans.",
                    }
                )
            current += datetime.timedelta(days=1)

        if not events:
            return None

        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": (today + datetime.timedelta(days=14)).isoformat(),
                "deals": events,
                "items_scraped": len(events),
            }
        )
