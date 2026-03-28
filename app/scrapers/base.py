from abc import ABC, abstractmethod
from typing import List, Dict
from playwright.async_api import Page

class BaseScraper(ABC):
    store_name: str = "Unknown Store"

    @abstractmethod
    async def scrape(self, page: Page) -> List[Dict]:
        """
        Scrape the weekly ad from the given playwright page.
        Returns a list of dicts with keys: name, price, description.
        """
        pass
