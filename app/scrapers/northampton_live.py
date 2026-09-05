from .base import BaseScraper
from playwright.async_api import Page
from typing import Dict, Optional
import datetime
import logging
import re
from urllib.parse import urljoin
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class NorthamptonLiveScraper(BaseScraper):
    store_name: str = "Northampton Live"
    scraper_key: str = "northampton_live"
    kind: str = "event"
    calendar_url: str = "https://northampton.live/calendar"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info("Scraping Northampton Live calendar...")
        try:
            await page.goto(self.calendar_url, wait_until="domcontentloaded", timeout=30000)
            event_links = page.locator("#calendar .event.upcoming a")
            await event_links.first.wait_for(state="visible", timeout=15000)
            detail_page = await page.context.new_page()

            events = []
            try:
                for index in range(min(await event_links.count(), 20)):
                    link = event_links.nth(index)
                    name = (await link.inner_text()).strip()
                    title = (await link.get_attribute("title") or "").strip()
                    href = await link.get_attribute("href")
                    if not name:
                        continue

                    date_label = await link.evaluate(
                        "element => element.closest('td')?.querySelector('.header')?.textContent?.replace(/\\s+/g, ' ')?.trim() || ''"
                    )
                    date_label = date_label or self._extract_date_label(title)
                    time_label, location_label, detail_text = await self._read_event_details(
                        detail_page,
                        urljoin(self.calendar_url, href) if href else None,
                    )
                    event_label = time_label or date_label or "See event details"
                    detail_parts = [part for part in (location_label, detail_text) if part]
                    if href:
                        detail_parts.append(f"Details: {urljoin(self.calendar_url, href)}")
                    events.append(
                        {
                            "name": name,
                            "price": event_label,
                            "description": " | ".join(detail_parts),
                        }
                    )
            finally:
                await detail_page.close()

            if not events:
                logger.warning("Northampton Live calendar returned no upcoming events")
                return None

            today = utcnow().date()
            return self.build_result(
                {
                    "flyer_start_date": today.isoformat(),
                    "flyer_end_date": (today + datetime.timedelta(days=14)).isoformat(),
                    "deals": events,
                    "items_scraped": await event_links.count(),
                }
            )
        except Exception as e:
            logger.error("Error scraping Northampton Live: %s", e)
            return None

    @staticmethod
    def _extract_date_label(title: str) -> str:
        if not title:
            return ""
        match = re.search(r"\((.+)\)$", title)
        return match.group(1) if match else ""

    @staticmethod
    async def _read_event_details(page: Page, url: Optional[str]):
        if not url:
            return "", "", ""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            time_label = (await page.locator('time[itemprop="startDate"]').first.inner_text()).strip()
            location_label = (await page.locator('[itemprop="location"]').first.inner_text()).strip()
            description_locator = page.locator('[itemprop="description"]').first
            detail_text = (await description_locator.inner_text()).strip() if await description_locator.count() else ""
            return time_label, location_label, detail_text
        except Exception as e:
            logger.info("Could not read Northampton Live event details from %s: %s", url, e)
            return "", "", ""
