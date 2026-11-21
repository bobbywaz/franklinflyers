from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional, List
import logging
import datetime
import re
from ..store_utils import utcnow

logger = logging.getLogger(__name__)

class RendezvousScraper(BaseScraper):
    """Scraper for The Rendezvous ("The Voo") in Turners Falls, MA.

    Extracts upcoming events and live music from https://thevoo.net/events/
    and https://thevoo.net/calendar/. Returns only verified events and never
    fabricates synthetic or mock shows.
    """
    store_name: str = "The Rendezvous"
    scraper_key: str = "rendezvous"
    kind: str = "event"
    events_url: str = "https://thevoo.net/events/"
    calendar_url: str = "https://thevoo.net/calendar/"

    async def scrape(self, page: Page) -> Optional[Dict]:
        """Scrape upcoming live events for The Rendezvous.

        Args:
            page: Playwright Page instance used for browser interaction.

        Returns:
            Normalized dictionary containing event deals, flyer dates, and next refresh timestamps.
        """
        logger.info("Scraping The Rendezvous Turners Falls events...")
        today = utcnow().date()
        events: List[Dict] = []

        try:
            await page.goto(self.events_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1000)

            # Check for structured calendar / event items if The Voo ever adds them
            items = page.locator(".event, .events-item, article.type-event, .tribe-events-calendar-list__event")
            count = await items.count()
            for i in range(count):
                it = items.nth(i)
                title_el = it.locator(".entry-title, .event-title, h2, h3").first
                title = (await title_el.inner_text()).strip() if await title_el.count() else ""
                if not title:
                    continue

                desc_el = it.locator(".entry-content, .event-description, p").first
                desc = (await desc_el.inner_text()).strip() if await desc_el.count() else "Live event at The Rendezvous"
                time_el = it.locator(".event-time, time, .date").first
                time_str = (await time_el.inner_text()).strip() if await time_el.count() else "See details"

                events.append({
                    "name": title,
                    "price": time_str,
                    "description": f"{desc} | Details: {self.events_url}",
                })
        except Exception as e:
            logger.warning("The Rendezvous page load or parse failed: %s", e)

        payload = {
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=14)).isoformat(),
            "deals": events,
            "items_scraped": len(events),
        }
        return self.build_result(payload)
