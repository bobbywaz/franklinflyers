import logging
import requests
import os
import json
import asyncio
import google.generativeai as genai
import base64
from .base import BaseScraper
from typing import List, Dict
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class StopAndShopScraper(BaseScraper):
    store_name = "Stop & Shop"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} Greenfield weekly ad...")
        
        # 0442 is the store code for Greenfield, MA Stop & Shop
        url = "https://stopandshop.com/weekly-ad?storeCode=0442"
        
        try:
            cookies, ua = await self._get_flaresolverr_cookies(url)
            if cookies:
                await page.context.add_cookies(cookies)
                if ua:
                    await page.set_extra_http_headers({"User-Agent": ua})
        except Exception as e:
            logger.warning(f"Failed to use FlareSolverr for Stop & Shop: {e}")

        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await page.wait_for_timeout(10000)
            
            content = await page.content()
            if "captcha" in content.lower() or "datadome" in content.lower():
                logger.error("Stop & Shop blocked by CAPTCHA")
                return []

            screenshot_path = "/tmp/ss_flyer.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Captured Stop & Shop flyer screenshot to {screenshot_path}")

            deals = await self._analyze_screenshot_with_gemini(screenshot_path)
            return deals

        except Exception as e:
            logger.error(f"Error scraping Stop & Shop: {e}")
            return []

    async def _get_flaresolverr_cookies(self, url: str):
        flaresolverr_url = "http://172.20.0.1:8191/v1"
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000
        }
        try:
            response = requests.post(flaresolverr_url, json=payload, timeout=70).json()
            if response.get('status') == 'ok':
                return response['solution']['cookies'], response['solution']['userAgent']
        except Exception as e:
            logger.error(f"FlareSolverr request failed for Stop & Shop: {e}")
        return None, None

    async def _analyze_screenshot_with_gemini(self, image_path: str) -> List[Dict]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return []

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_parts = [
                {
                    "mime_type": "image/png",
                    "data": image_data
                }
            ]
            
            prompt = """
            Look at this grocery store flyer and extract the top 15-20 deals.
            Crucially, look for the DATES on the flyer to ensure it is for the current week (early April 2026).
            If the flyer is for a different week, please still extract the deals but note the dates in the description.
            Also verify if it mentions 'Greenfield' or store '#0442'.

            For each deal, provide:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5")
            - description: Any additional details like size or brand (e.g. "12 oz pkg")

            Return the data ONLY as a JSON list of objects.
            """
            
            logger.info("Extracting Stop & Shop deals from screenshot with Gemini...")
            response = await asyncio.to_thread(model.generate_content, [prompt, image_parts[0]])
            
            text = response.text.strip()
            # Clean up potential markdown formatting
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            try:
                deals = json.loads(text)
                logger.info(f"Successfully extracted {len(deals)} deals from Stop & Shop screenshot")
                return deals
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON for Stop & Shop: {e}. Raw text: {text[:200]}...")
                return []
            
        except Exception as e:
            logger.error(f"Error analyzing Stop & Shop screenshot with Gemini: {e}")
            return []
