import logging
import httpx
import os
import json
import asyncio
import google.generativeai as genai
from .base import BaseScraper
from typing import List, Dict
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class BigYScraper(BaseScraper):
    store_name: str = "Big Y"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} Greenfield weekly ad...")
        # Big Y weekly ad URL, attempting to include ZIP or targeting the flyer view
        url = "https://www.bigy.com/weekly-ad/flyerview"
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            # Big Y takes a while to load the circular
            await page.wait_for_timeout(10000)
            
            # Look for Greenfield ZIP in the page to verify
            # Or just take a screenshot and let Gemini verify
            
            screenshot_path = "/tmp/bigy_flyer.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Captured Big Y flyer screenshot to {screenshot_path}")

            deals = await self._analyze_screenshot_with_gemini(screenshot_path)
            return deals

        except Exception as e:
            logger.error(f"Error scraping Big Y: {e}")
            return []

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
            Extract the top 15-20 grocery deals from this Big Y weekly flyer screenshot.
            Crucially, look for the DATES on the flyer to ensure it is for the current week (April 2026).
            Verify if it's for the Greenfield, MA store if mentioned.

            For each deal, provide:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5", "BOGO")
            - description: Any additional details like size, brand, or "With Big Y Membership" details

            Return the data ONLY as a JSON list of objects.
            """
            
            logger.info("Extracting Big Y deals from screenshot with Gemini...")
            response = await asyncio.to_thread(model.generate_content, [prompt, image_parts[0]])
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            try:
                deals = json.loads(text)
                logger.info(f"Successfully extracted {len(deals)} deals from Big Y screenshot")
                return deals
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON for Big Y: {e}. Raw text: {text[:200]}...")
                return []
            
        except Exception as e:
            logger.error(f"Error analyzing Big Y screenshot with Gemini: {e}")
            return []
