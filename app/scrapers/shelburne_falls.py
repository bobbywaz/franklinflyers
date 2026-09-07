from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
from urllib.parse import urljoin
from ..store_utils import utcnow
from ..store_utils import parse_date_value

logger = logging.getLogger(__name__)


class ShelburneFallsScraper(BaseScraper):
    """Scraper for the Shelburne Falls community events calendar.

    Paginates through https://www.shelburnefalls.com/calendar/ to extract
    event titles, dates, start times, venues, and detail links directly without AI.
    """
    store_name: str = "Shelburne Falls Calendar"
    scraper_key: str = "shelburne_falls"
    kind: str = "event"
    calendar_url: str = "https://www.shelburnefalls.com/calendar/"

    async def scrape(self, page: Page) -> Optional[Dict]:
        """Scrape active events from Shelburne Falls calendar pages.

        Args:
            page: Playwright Page instance used to paginate through calendar pages.

        Returns:
            Normalized dictionary built via BaseScraper.build_result().
        """
        logger.info("Scraping Shelburne Falls calendar...")
        events = []
        event_dates = []
        today = utcnow().date()
        total_cards_count = 0

        try:
            # Paginate up to 3 pages of upcoming community events
            for page_num in range(1, 4):
                page_url = f"https://www.shelburnefalls.com/calendar/?page={page_num}" if page_num > 1 else self.calendar_url
                try:
                    await page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                    cards = page.locator(".event-block")
                    if await cards.count() == 0:
                        break
                    count = await cards.count()
                    total_cards_count += count
                    for index in range(count):
                        card = cards.nth(index)
                        title_link = card.locator("a.title").first
                        name = (await title_link.inner_text()).strip() if await title_link.count() else ""
                        href = await title_link.get_attribute("href") if await title_link.count() else ""
                        date_label = (await card.locator(".date").inner_text()).strip() if await card.locator(".date").count() else ""
                        parsed_date = parse_date_value(date_label, today)
                        if parsed_date:
                            event_dates.append(parsed_date)
                        time_label = (await card.locator(".start-time").inner_text()).strip() if await card.locator(".start-time").count() else ""
                        street_locator = card.locator(".street1").first
                        city_locator = card.locator(".city-state-zip").first
                        street = (await street_locator.inner_text()).strip() if await street_locator.count() else ""
                        city = (await city_locator.inner_text()).strip() if await city_locator.count() else ""
                        detail_url = urljoin(self.calendar_url, href) if href else self.calendar_url
                        label = f"{date_label} | {time_label}".strip(" |")
                        parts = [part for part in (f"{street}, {city}".strip(", "),) if part]
                        parts.append(f"Details: {detail_url}")
                        events.append(
                            {
                                "name": name,
                                "price": label,
                                "description": " | ".join(parts),
                            }
                        )
                except Exception as pe:
                    logger.warning("Error fetching Shelburne Falls page %s: %s", page_num, pe)
                    break
        except Exception as e:
            logger.error("Shelburne Falls calendar failed to load: %s", e)
            return None

        if not events:
            return None

        flyer_end = max(event_dates, default=today + datetime.timedelta(days=14))
        if flyer_end < today + datetime.timedelta(days=14):
            flyer_end = today + datetime.timedelta(days=14)

        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": flyer_end.isoformat(),
                "deals": events,
                "items_scraped": total_cards_count,
            }
        )

    @staticmethod
    async def _read_detail(page: Page, url: str) -> str:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            description = page.locator('meta[name="description"]').first
            return (await description.get_attribute("content") or "").strip()
        except Exception as e:
            logger.info("Could not read Shelburne Falls event details from %s: %s", url, e)
            return ""
