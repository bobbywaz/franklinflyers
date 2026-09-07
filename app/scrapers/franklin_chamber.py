from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
import re
from urllib.parse import quote, urljoin

from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class FranklinChamberScraper(BaseScraper):
    """Scraper for the Franklin County Chamber of Commerce community calendar.

    Extracts regional Franklin County happenings, farmers markets, and civic
    events from https://chamber.franklincc.org/events/calendar/, with fallback to
    the rolling list view and resilient regional event defaults.
    """
    store_name: str = "Franklin County Chamber Events"
    scraper_key: str = "franklin_chamber"
    kind: str = "event"
    calendar_url: str = "https://chamber.franklincc.org/events"

    async def scrape(self, page: Page) -> Optional[Dict]:
        """Scrape current month events from the Franklin County Chamber calendar.

        Args:
            page: Playwright Page instance used for browser interaction.

        Returns:
            Normalized dictionary containing event deals, flyer dates, and next refresh timestamps.
        """
        today = utcnow().date()
        cal_url = f"https://chamber.franklincc.org/events/calendar/{today.year}-{today.month:02d}-01"
        logger.info("Scraping Franklin County Chamber events from %s", cal_url)

        events = []
        event_dates = []


        # Try scraping the full monthly calendar view first
        try:
            await page.goto(cal_url, wait_until="domcontentloaded", timeout=25000)
            day_cells = page.locator("td.gz-cal-days")
            cell_count = await day_cells.count()
            if cell_count > 0:
                for i in range(cell_count):
                    cell = day_cells.nth(i)
                    day_link = cell.locator("a[href*='/events/index/']").first
                    if await day_link.count() == 0:
                        continue
                    day_href = await day_link.get_attribute("href") or ""
                    m = re.search(r"\d{4}-\d{2}-\d{2}", day_href)
                    if not m:
                        continue
                    day_str = m.group(0)
                    try:
                        event_date = datetime.date.fromisoformat(day_str)
                    except ValueError:
                        continue
                    if event_date < today:
                        continue

                    ev_links = cell.locator("a[href*='/events/details/']")
                    ev_count = await ev_links.count()
                    for j in range(ev_count):
                        el = ev_links.nth(j)
                        name = (await el.inner_text()).strip()
                        href = await el.get_attribute("href") or ""
                        if not name:
                            continue
                        detail_url = urljoin(self.calendar_url, href) if href else self.calendar_url
                        date_label = event_date.strftime("%A, %B %-d")
                        event_dates.append(event_date)
                        events.append(
                            {
                                "name": name,
                                "price": date_label,
                                "description": f"Details: {detail_url}",
                            }
                        )
        except Exception as e:
            logger.warning("Franklin County Chamber calendar view load failed: %s; trying card view", e)

        # Fallback to the rolling event cards view if calendar view yielded nothing
        if not events:
            try:
                await page.goto(self.calendar_url, wait_until="domcontentloaded", timeout=25000)
                cards = page.locator(".gz-events-card")
                await cards.first.wait_for(state="visible", timeout=10000)
                detail_page = await page.context.new_page()
                try:
                    for index in range(await cards.count()):
                        card = cards.nth(index)
                        title_link = card.locator(".gz-card-title a").first
                        name = (await title_link.inner_text()).strip()
                        href = await title_link.get_attribute("href")
                        date_span = card.locator(".gz-card-date span[content]").first
                        start_value = await date_span.get_attribute("content") if await date_span.count() else None
                        end_value = await card.locator(".gz-card-date meta").first.get_attribute("content") if await card.locator(".gz-card-date meta").count() else None
                        if not name or not start_value:
                            continue

                        try:
                            start = datetime.datetime.fromisoformat(start_value)
                            event_dates.append(start.date())
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
            except Exception as e:
                logger.error("Franklin County Chamber event page failed to load: %s", e)

        if not events:
            logger.warning("Franklin County Chamber returned no upcoming events")
            return None

        flyer_end = max(event_dates, default=today + datetime.timedelta(days=14))
        if flyer_end < today + datetime.timedelta(days=14):
            flyer_end = today + datetime.timedelta(days=14)

        return self.build_result(
            {
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": flyer_end.isoformat(),
                "deals": events,
                "items_scraped": len(events),
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
