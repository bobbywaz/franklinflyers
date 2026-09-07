import datetime
import logging
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseScraper
from ..store_utils import utcnow

logger = logging.getLogger(__name__)


class PharmacyFlippScraper(BaseScraper):
    """Base scraper for pharmacies utilizing the Flipp Backflipp circular API.

    Queries the Backflipp items search endpoint with store-specific postal codes
    and merchant queries, extracting product promotions, categories, price stories,
    and product images. Falls back to curated seasonal/weekly pharmacy deals if the
    API is unreachable.
    """
    kind: str = "pharmacy"
    postal_code: str = "01301"
    flipp_search_query: str = ""
    merchant_keyword: str = ""
    flipp_search_url: str = "https://backflipp.wishabi.com/flipp/items/search"
    fallback_deals: List[Dict[str, Any]] = []

    async def scrape(self, page=None) -> Optional[Dict[str, Any]]:
        """Fetch weekly circular promotions via Flipp search API with fallback.

        Args:
            page: Optional Playwright Page instance (used if direct HTTP fails).

        Returns:
            Normalized dictionary containing deals, dates, and refresh timestamps.
        """
        logger.info("Scraping weekly pharmacy deals for %s in %s...", self.store_name, self.postal_code)
        items = await self._fetch_flipp_items(page=page)

        if not items:
            logger.warning(
                "No live items returned for %s (%s). Using curated fallback deals.",
                self.store_name,
                self.postal_code,
            )
            deals = list(self.fallback_deals)
            now = utcnow()
            today = now.date()
            payload = {
                "deals": deals,
                "items_scraped": len(deals),
                "flyer_start_date": today.isoformat(),
                "flyer_end_date": (today + datetime.timedelta(days=7)).isoformat(),
                "expires_at": now + datetime.timedelta(days=7),
                "next_refresh_at": now + datetime.timedelta(days=1),
            }
            return self.build_result(payload)

        payload = self._build_payload_from_items(items)
        if not payload.get("deals"):
            logger.warning("Parsed 0 deals from %d items for %s. Using fallbacks.", len(items), self.store_name)
            payload["deals"] = list(self.fallback_deals)
            payload["items_scraped"] = len(self.fallback_deals)

        return self.build_result(payload)

    async def _fetch_flipp_items(self, page=None) -> List[Dict[str, Any]]:
        """Query Backflipp items search endpoint with resilience."""
        params = {
            "locale": "en-us",
            "postal_code": self.postal_code,
            "q": self.flipp_search_query,
        }

        # 1. Direct async HTTP request
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as client:
                resp = await client.get(self.flipp_search_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    all_items = data.get("items") or []
                    filtered = self._filter_merchant_items(all_items)
                    if filtered:
                        return filtered
        except Exception as e:
            logger.warning("Direct HTTP search for %s failed: %s", self.store_name, e)

        # 2. Browser page fallback if available
        if page is not None:
            try:
                target_url = f"{self.flipp_search_url}?locale=en-us&postal_code={self.postal_code}&q={self.flipp_search_query}"
                resp = await page.request.get(target_url, timeout=20000)
                if resp.ok:
                    data = await resp.json()
                    all_items = data.get("items") or []
                    filtered = self._filter_merchant_items(all_items)
                    if filtered:
                        return filtered
            except Exception as pe:
                logger.warning("Playwright request fallback failed for %s: %s", self.store_name, pe)

        return []

    def _filter_merchant_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items matching the expected merchant name."""
        kw = self.merchant_keyword.lower()
        if not kw:
            return items
        filtered = []
        for item in items:
            merchant_name = str(item.get("merchant_name") or "").lower()
            if kw in merchant_name:
                filtered.append(item)
        return filtered

    def _build_payload_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert raw Flipp item dicts into normalized deals and dates."""
        deals = []
        seen = set()
        flyer_start: Optional[datetime.date] = None
        flyer_end: Optional[datetime.date] = None

        for item in items:
            start = self._parse_iso_date(item.get("valid_from"))
            end = self._parse_iso_date(item.get("valid_to"))
            if start and (flyer_start is None or start < flyer_start):
                flyer_start = start
            if end and (flyer_end is None or end > flyer_end):
                flyer_end = end

            name = str(item.get("name") or "").strip()
            if not name:
                continue

            price = self._format_price(item)
            desc = self._format_description(item, used_sale_story=(price == str(item.get("sale_story") or "").strip()))

            key = (name.lower(), price.lower())
            if key in seen:
                continue
            seen.add(key)

            deals.append({
                "name": name,
                "price": price,
                "description": desc,
            })

        now = utcnow()
        today = now.date()
        start_date = flyer_start or today
        end_date = flyer_end or (start_date + datetime.timedelta(days=7))

        expires_at = datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
        next_refresh = max(now + datetime.timedelta(hours=6), expires_at - datetime.timedelta(days=1))

        return {
            "deals": deals,
            "items_scraped": len(deals),
            "flyer_start_date": start_date.isoformat(),
            "flyer_end_date": end_date.isoformat(),
            "expires_at": expires_at,
            "next_refresh_at": next_refresh,
        }

    def _format_price(self, item: Dict[str, Any]) -> str:
        """Format price string from Flipp numeric or text fields."""
        cur = item.get("current_price")
        pre = str(item.get("pre_price_text") or "").strip()
        post = str(item.get("post_price_text") or "").strip()
        price_text = str(item.get("price_text") or "").strip()
        sale_story = str(item.get("sale_story") or "").strip()

        if cur not in (None, ""):
            if isinstance(cur, (int, float)):
                if isinstance(cur, float) and cur.is_integer():
                    price_str = f"${int(cur)}"
                elif isinstance(cur, float):
                    price_str = f"${cur:.2f}"
                else:
                    price_str = f"${cur}"
            else:
                price_str = f"${cur}"

            parts = []
            if pre:
                parts.append(pre)
            parts.append(price_str)
            if post:
                parts.append(post)
            return " ".join(parts).strip()

        if price_text:
            return price_text

        if sale_story:
            return sale_story

        return "See store for pricing"

    def _format_description(self, item: Dict[str, Any], used_sale_story: bool = False) -> str:
        """Extract category, promotional notes, brand, and clipping image."""
        parts = []
        l1 = str(item.get("_L1") or "").strip()
        l2 = str(item.get("_L2") or "").strip()
        category = " • ".join(filter(None, [l1, l2]))
        if category:
            parts.append(category)

        desc = str(item.get("description") or "").strip()
        if desc:
            parts.append(desc)

        sale_story = str(item.get("sale_story") or "").strip()
        if not used_sale_story and sale_story:
            parts.append(sale_story)

        image_url = item.get("clipping_image_url") or item.get("clean_image_url") or item.get("image_url")
        if image_url:
            parts.append(f"Image: {image_url}")

        return " | ".join(parts) if parts else "Weekly pharmacy circular item."

    def _parse_iso_date(self, value: Optional[str]) -> Optional[datetime.date]:
        """Safely parse ISO date or datetime string."""
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(value).date()
        except Exception:
            return None
