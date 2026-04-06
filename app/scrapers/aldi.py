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

class AldiScraper(BaseScraper):
    store_name = "ALDI"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} Greenfield weekly ad...")
        
        # ALDI's weekly ad URL for the Greenfield area (ZIP 01301)
        # Adding zipCode parameter directly to the URL
        url = "https://info.aldi.us/weekly-specials/weekly-ads?zipCode=01301"
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for the Flipp/circular widget to load
            # ALDI can be slow to render the flyer content
            await page.wait_for_timeout(10000)
            
            # Take a screenshot of the flyer area
            screenshot_path = "/tmp/aldi_flyer.png"
            # We want to capture enough of the flyer to see deals and dates
            await page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Captured ALDI flyer screenshot to {screenshot_path}")

            # Use Gemini to analyze the screenshot
            deals = await self._analyze_screenshot_with_gemini(screenshot_path)
            
            # If vision fails or returns very few deals, we could try a fallback
            # but usually vision is robust for these complex JS flyers
            return deals

        except Exception as e:
            logger.error(f"Error scraping ALDI: {e}")
            return []

    async def _analyze_screenshot_with_gemini(self, image_path: str) -> List[Dict]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return []

        try:
            genai.configure(api_key=api_key)
            # Use 2.5 flash as it's the latest confirmed working model in our tests
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
            Extract the top 15-20 grocery deals from this ALDI flyer screenshot.
            Crucially, look for the DATES on the flyer (e.g. "Valid April 1 - April 7") to ensure it is for the current week (early April 2026).
            If the flyer is for a different week, please still extract the deals but note the dates in the description.
            Also verify if it mentions 'Greenfield' or '01301'.

            For each deal, provide:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99", "$2.49/lb", "2 for $5")
            - description: Any additional details like size, brand, or 'ALDI Find' status (e.g. "1 lb pkg", "Specially Selected")

            Return the data ONLY as a JSON list of objects.
            """
            
            logger.info("Extracting ALDI deals from screenshot with Gemini...")
            response = await asyncio.to_thread(model.generate_content, [prompt, image_parts[0]])
            
            text = response.text.strip()
            # Clean up potential markdown formatting
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            try:
                deals = json.loads(text)
                logger.info(f"Successfully extracted {len(deals)} deals from ALDI screenshot")
                return deals
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini JSON for ALDI: {e}. Raw text: {text[:200]}...")
                return []
            
        except Exception as e:
            logger.error(f"Error analyzing ALDI screenshot with Gemini: {e}")
            # Fallback placeholder if Gemini fails during development
            return []
