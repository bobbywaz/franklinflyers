from abc import ABC, abstractmethod
from typing import Dict
from playwright.async_api import Page
from ..store_utils import build_grocery_result

class BaseScraper(ABC):
    store_name: str = "Unknown Store"
    scraper_key: str = "unknown"
    kind: str = "grocery"

    @abstractmethod
    async def scrape(self, page: Page) -> Dict:
        """
        Scrape the weekly ad from the given playwright page.
        """
        pass

    def build_result(self, payload) -> Dict:
        res = build_grocery_result(self.scraper_key, self.store_name, payload)
        res["kind"] = self.kind
        return res
