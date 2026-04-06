from typing import List, Dict
from playwright.async_api import Page
import logging
import asyncio
import re
import requests
import json

logger = logging.getLogger(__name__)

class GasScraper:
    def __init__(self):
        # GasBuddy city pages
        self.cities = [
            {"name": "Greenfield", "url": "https://www.gasbuddy.com/gasprices/massachusetts/greenfield"},
            {"name": "Turners Falls", "url": "https://www.gasbuddy.com/gasprices/massachusetts/turners-falls"},
            {"name": "Gill", "url": "https://www.gasbuddy.com/gasprices/massachusetts/gill"}
        ]
        self.flaresolverr_url = "http://172.20.0.1:8191/v1"

    async def _get_flaresolverr_cookies(self, url: str):
        """
        Request cookies and User-Agent from FlareSolverr.
        """
        logger.info(f"Getting FlareSolverr cookies for {url}...")
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000
        }
        try:
            response = requests.post(self.flaresolverr_url, json=payload, timeout=70).json()
            if response.get('status') == 'ok':
                return response['solution']['cookies'], response['solution']['userAgent']
            else:
                logger.warning(f"FlareSolverr returned status: {response.get('status')}")
        except Exception as e:
            logger.error(f"FlareSolverr request failed: {e}")
        return None, None

    async def scrape(self, page: Page, run_date: str = None) -> List[Dict]:
        """
        Scrape gas prices from GasBuddy, extracting from Apollo state for real-time data.
        """
        all_prices = []
        
        # Try FlareSolverr once
        cookies, user_agent = await self._get_flaresolverr_cookies("https://www.gasbuddy.com")
        if cookies:
            await page.context.add_cookies(cookies)

        for city in self.cities:
            try:
                logger.info(f"Scraping GasBuddy prices for {city['name']}...")
                await page.goto(city['url'], wait_until="load", timeout=60000)
                
                # Check for Cloudflare challenge
                title = await page.title()
                if "Just a moment..." in title or "Cloudflare" in title:
                    logger.warning(f"Cloudflare detected for {city['name']}, waiting...")
                    await asyncio.sleep(10)

                # Extract from __APOLLO_STATE__
                content = await page.content()
                match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', content, re.DOTALL)
                
                if match:
                    try:
                        apollo_data = json.loads(match.group(1))
                        
                        # 1. Map station IDs to their display names and addresses
                        stations = {}
                        for key, value in apollo_data.items():
                            if key.startswith("Station:") and value.get("__typename") == "Station":
                                sid = value.get("id")
                                name = value.get("name", "Unknown")
                                addr_obj = value.get("address", {})
                                address = addr_obj.get("line1", "Unknown")
                                stations[sid] = {"name": name, "address": address, "id": sid}

                        # 2. Extract price reports linked to these stations
                        city_results = []
                        seen_sids = set()

                        for key, value in apollo_data.items():
                            if value.get("__typename") == "PriceReport" and value.get("fuelProduct") == "regular_gas":
                                # Extract station ID from key (e.g., PriceReport:76743:1:0)
                                parts = key.split(':')
                                if len(parts) >= 2:
                                    sid = parts[1]
                                    if sid in stations and sid not in seen_sids:
                                        station = stations[sid]
                                        
                                        # Get price and time
                                        p_data = value.get("credit") or value.get("cash")
                                        if p_data:
                                            price_val = p_data.get("price")
                                            raw_time = p_data.get("postedTime")
                                            
                                            if price_val:
                                                price_str = f"${price_val:.2f}"
                                                
                                                # Convert ISO time to relative time (simplified)
                                                source_time = "Recent"
                                                if raw_time:
                                                    source_time = raw_time # Keeping ISO for now to be exact
                                                
                                                name = station['name']
                                                if city['name'] == "Gill" and "mobil" in name.lower():
                                                    name = "The Mill"

                                                city_results.append({
                                                    "station_name": name,
                                                    "address": station['address'],
                                                    "city": city['name'],
                                                    "price": price_str,
                                                    "fuel_type": "Regular",
                                                    "updated_at": run_date,
                                                    "source_updated_at": source_time
                                                })
                                                seen_sids.add(sid)
                                                logger.info(f"Extracted from Apollo: {name} in {city['name']}: {price_str} ({source_time})")

                        if city_results:
                            all_prices.extend(city_results)
                            continue # Successfully found prices via Apollo for this city

                    except Exception as e:
                        logger.error(f"Error parsing Apollo state for {city['name']}: {e}")

                # Strategy 2: Improved DOM Extraction (Fallback)
                # This part is mostly for robustness if Apollo state changes format
                try:
                    await page.wait_for_selector("[class*='StationDisplay']", timeout=20000)
                except:
                    logger.warning(f"Timeout waiting for StationDisplay in {city['name']}")

                await asyncio.sleep(2)
                stations_elements = await page.query_selector_all("[class*='StationDisplay-module__station']")
                
                city_seen = set()
                for station in stations_elements:
                    text = await station.inner_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    if len(lines) >= 3:
                        name = lines[0]
                        address = lines[1]
                        price = "Unknown"
                        source_time = "Unknown"
                        
                        for i, line in enumerate(lines):
                            if re.match(r'\$\d\.\d{2}', line):
                                price = line
                                for j in range(i+1, min(i+5, len(lines))):
                                    if any(word in lines[j].lower() for word in ["ago", "minutes", "hours", "day"]):
                                        source_time = lines[j]
                                        break
                                break
                        
                        if city['name'] == "Gill" and "mobil" in name.lower():
                            name = "The Mill"

                        norm_key = (name.lower().strip(), address.lower().strip())
                        if norm_key not in city_seen and price != "Unknown":
                            all_prices.append({
                                "station_name": name,
                                "address": address,
                                "city": city['name'],
                                "price": price,
                                "fuel_type": "Regular",
                                "updated_at": run_date,
                                "source_updated_at": source_time
                            })
                            city_seen.add(norm_key)
                            logger.info(f"Fallback DOM Scrape: {name} in {city['name']}: {price} ({source_time})")

            except Exception as e:
                logger.error(f"Error scraping {city['name']}: {e}")
        
        return all_prices
