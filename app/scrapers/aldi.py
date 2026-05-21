import logging
import os
import json
import asyncio
from google import genai
from google.genai import types
from .base import BaseScraper
from typing import Dict, Optional
from playwright.async_api import Page
from ..store_utils import parse_gemini_json

logger = logging.getLogger(__name__)

class AldiScraper(BaseScraper):
    store_name = "ALDI"
    scraper_key = "aldi"
    zip_code = "01376"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info(f"Navigating to {self.store_name} Greenfield weekly ad...")

        url = f"https://info.aldi.us/weekly-specials/weekly-ads?zipCode={self.zip_code}"

        try:
            await page.set_viewport_size({"width": 1600, "height": 2400})
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            await self._dismiss_cookie_banner(page)
            await self._load_greenfield_flyer(page)

            screenshot_path = "/tmp/aldi_flyer.png"
            await page.frame_locator('iframe[title="Main Panel"]').locator("canvas").first.screenshot(path=screenshot_path)
            logger.info(f"Captured ALDI flyer screenshot to {screenshot_path}")

            analysis = await self._analyze_screenshot_with_gemini(screenshot_path)
            if analysis is None:
                return None
            return self.build_result(analysis)

        except Exception as e:
            logger.error(f"Error scraping ALDI: {e}")
            return None

    async def _dismiss_cookie_banner(self, page: Page) -> None:
        try:
            await page.get_by_role("button", name="Accept All").click(timeout=5000)
            await page.wait_for_timeout(1000)
        except Exception:
            logger.info("ALDI cookie banner was not shown or could not be dismissed")

    async def _load_greenfield_flyer(self, page: Page) -> None:
        info_frame = page.frame_locator('iframe[title="Information Panel"]')
        main_frame = page.frame_locator('iframe[title="Main Panel"]')

        zip_input = info_frame.get_by_placeholder("Enter your ZIP Code")
        await zip_input.wait_for(timeout=15000)
        await zip_input.fill(self.zip_code)
        await info_frame.get_by_role("button", name="Find Stores").click()

        greenfield_result = info_frame.locator("text=Aldi, Greenfield")
        await greenfield_result.wait_for(timeout=15000)
        await info_frame.get_by_role("button", name="Select").first.click()

        await main_frame.locator("text=Selected").first.wait_for(timeout=20000)
        await page.wait_for_timeout(3000)

    async def _analyze_screenshot_with_gemini(self, image_path: str) -> Optional[Dict]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return None

        try:
            client = genai.Client(api_key=api_key)
            # Use 2.5 flash as it's the latest confirmed working model in our tests
            pass  # model instantiation removed
            
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            image_parts = [
                types.Part.from_bytes(data=image_data, mime_type="image/png")
            ]
            
            prompt = """
            Extract the top 15-20 grocery deals from this ALDI flyer screenshot and identify the flyer validity dates.
            Also verify if it mentions 'Greenfield' or '01376'.

            Return ONLY a JSON object with:
            - items_scraped: the total number of distinct priced items you read across the flyer before choosing the best deals
            - flyer_start_date: the flyer start date in YYYY-MM-DD when possible
            - flyer_end_date: the flyer end date in YYYY-MM-DD when possible
            - deals: a JSON list of objects

            Each deal object must include:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99", "$2.49/lb", "2 for $5")
            - description: Any additional details like size, brand, or 'ALDI Find' status (e.g. "1 lb pkg", "Specially Selected")
            """
            
            logger.info("Extracting ALDI deals from screenshot with Gemini...")
            response = await asyncio.to_thread(client.models.generate_content, model='gemini-2.5-flash', contents=[prompt, image_parts[0]])
            
            try:
                parsed = parse_gemini_json(response.text)
                deal_count = len(parsed.get("deals", parsed if isinstance(parsed, list) else []))
                logger.info(f"Successfully extracted {deal_count} deals from ALDI screenshot")
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse Gemini JSON for ALDI: {e}. Raw text: {response.text[:200]}...")
                return None
            
        except Exception as e:
            logger.error(f"Error analyzing ALDI screenshot with Gemini: {e}")
            return None
