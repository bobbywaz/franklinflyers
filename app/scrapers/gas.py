from typing import List, Dict
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

class GasScraper:
    def __init__(self):
        self.cities = [
            {"name": "Greenfield", "url": "https://dmv-test-pro.com/gas-prices/massachusetts/greenfield"},
            {"name": "Turners Falls", "url": "https://dmv-test-pro.com/gas-prices/massachusetts/turners-falls"}
        ]

    async def scrape(self, page: Page) -> List[Dict]:
        """
        Scrape gas prices from dmv-test-pro.com.
        """
        all_prices = []
        for city in self.cities:
            try:
                logger.info(f"Scraping gas prices for {city['name']}...")
                await page.goto(city['url'], wait_until="networkidle")
                
                # Wait for gas items to load
                await page.wait_for_selector(".gas-tab-item", timeout=10000)
                
                items = await page.query_selector_all(".gas-tab-item")

                city_stations = set()
                for item in items:
                    name_el = await item.query_selector(".tab-item-title")
                    address_el = await item.query_selector(".tab-item-des")
                    price_el = await item.query_selector(".tab-item-price")

                    if name_el and price_el:
                        name = (await name_el.inner_text()).strip()
                        address = (await address_el.inner_text()).strip() if address_el else ""
                        price = (await price_el.inner_text()).strip()

                        # Only add if we haven't seen this station in this city yet
                        # This avoids adding Mid-grade/Premium prices which follow Regular
                        if name not in city_stations:
                            all_prices.append({
                                "station_name": name,
                                "address": address,
                                "city": city['name'],
                                "price": price,
                                "fuel_type": "Regular"
                            })
                            city_stations.add(name)

            except Exception as e:
                logger.error(f"Error scraping gas for {city['name']}: {e}")
        
        return all_prices
