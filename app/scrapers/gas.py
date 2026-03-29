from typing import List, Dict
from playwright.async_api import Page
import logging
import asyncio
import re

logger = logging.getLogger(__name__)

class GasScraper:
    def __init__(self):
        # GasBuddy city pages are more reliable for granular timestamps
        self.cities = [
            {"name": "Greenfield", "url": "https://www.gasbuddy.com/gasprices/massachusetts/greenfield"},
            {"name": "Turners Falls", "url": "https://www.gasbuddy.com/gasprices/massachusetts/turners-falls"},
            {"name": "Gill", "url": "https://www.gasbuddy.com/gasprices/massachusetts/gill"}
        ]

    async def scrape(self, page: Page, run_date: str = None) -> List[Dict]:
        """
        Scrape gas prices from GasBuddy.
        """
        all_prices = []
        for city in self.cities:
            try:
                logger.info(f"Scraping GasBuddy prices for {city['name']}...")
                # GasBuddy can be slow, use 'load' and a decent timeout
                await page.goto(city['url'], wait_until="load", timeout=60000)
                
                # Wait for station elements to load
                # GasBuddy uses classes that often contain 'StationDisplay'
                try:
                    await page.wait_for_selector("[class*='StationDisplay']", timeout=15000)
                except:
                    logger.warning(f"Timeout waiting for StationDisplay in {city['name']}, trying fallback...")

                # Buffer for dynamic content
                await asyncio.sleep(3)
                
                # Get all station containers
                stations = await page.query_selector_all("[class*='StationDisplay-module__station']")
                
                city_stations = set()
                for station in stations:
                    text = await station.inner_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    if len(lines) >= 3:
                        # GasBuddy layout is roughly:
                        # 0: Station Name
                        # 1: Address
                        # 2: Price (e.g. $3.69)
                        # 3: Reporter/Time (e.g. 11 Hours Ago)
                        
                        name = lines[0]
                        address = lines[1]
                        
                        # Find the first line that looks like a price ($X.XX)
                        price = "Unknown"
                        source_time = "Unknown"
                        
                        for i, line in enumerate(lines):
                            if re.match(r'\$\d\.\d{2}', line):
                                price = line
                                # The line after the price or containing "Ago" is usually the time
                                for j in range(i+1, min(i+4, len(lines))):
                                    if "Ago" in lines[j] or "minutes" in lines[j].lower() or "hours" in lines[j].lower():
                                        source_time = lines[j]
                                        break
                                break

                        # Rename 'Mobil' to 'The Mill' for Gill
                        if city['name'] == "Gill" and "mobil" in name.lower():
                            name = "The Mill"

                        if name not in city_stations and price != "Unknown":
                            all_prices.append({
                                "station_name": name,
                                "address": address,
                                "city": city['name'],
                                "price": price,
                                "fuel_type": "Regular",
                                "updated_at": run_date,
                                "source_updated_at": source_time
                            })
                            city_stations.add(name)
                            logger.info(f"Scraped {name} in {city['name']}: {price} ({source_time})")

            except Exception as e:
                logger.error(f"Error scraping GasBuddy for {city['name']}: {e}")
        
        return all_prices
