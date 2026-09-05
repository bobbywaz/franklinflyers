from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
from urllib.parse import quote, urljoin

from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class FranklinChamberScraper(BaseScraper):
    store_name: str = "Franklin County Chamber Events"
    scraper_key: str = "franklin_chamber"
    kind: str = "event"
    calendar_url: str = "https://chamber.franklincc.org/events"

    async def scrape(self, page: Page) -> Optional[Dict]:
        today = utcnow().date()
        end_date = today + datetime.timedelta(days=14)
        url = f"{self.calendar_url}?from={quote(today.strftime('%-m/%-d/%Y'))}&to={quote(end_date.strftime('%-m/%-d/%Y'))}"
        logger.info("Scraping Franklin County Chamber events from %s", url)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            cards = page.locator(".gz-events-card")
            await cards.first.wait_for(state="visible", timeout=15000)
            detail_page = await page.context.new_page()
        except Exception as e:
            logger.error("Franklin County Chamber event page failed to load: %s", e)
            return None

        events = []
        try:
            for index in range(min(await cards.count(), 30)):
                card = cards.nth(index)
                title_link = card.locator(".gz-card-title a").first
                name = (await title_link.inner_text()).strip()
                href = await title_link.get_attribute("href")
                date_span = card.locator(".gz-card-date span[content]").first
                start_value = await date_span.get_attribute("content")
                end_value = await card.locator(".gz-card-date meta").first.get_attribute("content")
                if not name or not start_value:
                    continue

                try:
                    start = datetime.datetime.fromisoformat(start_value)
                    end = datetime.datetime.fromisoformat(end_value) if end_value else None
                    date_label = start.strftime("%A, %B %-d, %-I:%M %p")
                    if end:
                        date_label += f"–{end.strftime('%-I:%M %p')}"
                except ValueError:
                    date_label = (await date_span.inner_text()).strip()

                detail_url = urljoin(self.calendar_url, href) if href else self.calendar_url
                detail_text, location_text = await self._read_event_details(detail_page, detail_url)
                detail_parts = [part for part in (location_text, detail_text) if part]
                detail_parts.append(f"Details: {detail_url}")
                events.append(
                    {
                        "name": name,
                        "price": date_label,
                        "description": " | ".join(detail_parts),
                    }
                )
        finally:
            await detail_page.close()

        if not events:
            logger.warning("Franklin County Chamber returned no upcoming events")
            return None

        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": end_date.isoformat(),
                "deals": events,
                "items_scraped": await cards.count(),
            }
        )

    @staticmethod
    async def _read_event_details(page: Page, url: str):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            description = (await page.locator(".gz-event-description").inner_text()).strip()
            location = (await page.locator(".gz-event-location [itemprop='name']").inner_text()).strip()
            return description[:1200], location
        except Exception as e:
            logger.info("Could not read Chamber event details from %s: %s", url, e)
            return "", ""
