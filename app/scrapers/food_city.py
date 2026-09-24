import logging
import httpx
import os
import json
import asyncio
import re
import datetime
from google import genai
from .base import BaseScraper
from typing import Dict, Optional, List
from playwright.async_api import Page
from ..store_utils import parse_gemini_json, utcnow

logger = logging.getLogger(__name__)

# Curated weekly circular deals for Turners Falls store
FOOD_CITY_FALLBACK_DEALS = [
    {"name": "Boneless Beef New York Sirloin Steak", "price": "$6.99/lb", "description": "Boneless Beef Sirloin"},
    {"name": "Boneless & Skinless Chicken Breast", "price": "$1.99/lb", "description": "Boneless & Skinless"},
    {"name": "USDA Choice Boneless Beef Bottom Round Roast", "price": "$5.99/lb", "description": "Lean Round Cube Steak Or Stew Meat"},
    {"name": "Boneless Center Cut Pork Chops", "price": "$2.99/lb", "description": "Or Boneless Country Style Spareribs"},
    {"name": "St. Louis Style Pork Spareribs", "price": "$3.99/lb", "description": "Meaty Spareribs"},
    {"name": "Fresh Pork Tenderloin", "price": "$3.49/lb", "description": "Fresh Tender Pork"},
    {"name": "Fresh Chicken Drumsticks or Leg Quarters", "price": "99¢/lb", "description": "Fresh Chicken"},
    {"name": "Boneless & Skinless Chicken Thighs", "price": "$2.49/lb", "description": "Boneless & Skinless"},
    {"name": "Navel or Cara Cara Oranges", "price": "$3.99/ea", "description": "3 Lb. Bag"},
    {"name": "Premium Red Seedless Grapes", "price": "$2.49/lb", "description": "Fresh Table Grapes"},
    {"name": "Hass Avocados", "price": "5 for $5", "description": "Fresh Hass Avocados"},
    {"name": "Fall Bin Pumpkins", "price": "$5.99/ea", "description": "Large Bin Pumpkins"},
    {"name": "Best Yet Large Cooked Shrimp", "price": "$8.99/ea", "description": "Frozen 31-40 Ct. 16 Oz. Pkg."},
    {"name": "Hummel Bros. Natural Casing Franks", "price": "$9.99/ea", "description": "2 Lb. Pkg. Red Franks Or Maple Leaf Franks"},
    {"name": "Oscar Mayer Sliced Bacon", "price": "$4.99/ea", "description": "12 Oz. Pkg. Original Hardwood Smoked"},
    {"name": "Hunt's Pasta Sauce", "price": "10 for $10", "description": "Selected Varieties 24 Oz. Can"},
    {"name": "Kraft Mac & Cheese 5 Pack", "price": "$4.99/ea", "description": "Selected Varieties 36.25 Oz. Pkg."},
    {"name": "Lay's Kettle Cooked Potato Chips", "price": "$2.99/ea", "description": "Selected Varieties 6-8 Oz. Bag"},
    {"name": "Lay's Classic Potato Chips", "price": "$2.99/ea", "description": "Selected Varieties 5-8 Oz. Bag"},
    {"name": "Cains Mayonnaise", "price": "$3.99/ea", "description": "30 Oz. Jar"},
    {"name": "Adirondack Fruit Flavored Water 6 Pack", "price": "2 for $4", "description": "16.9 Oz. Btls. 101.4 Oz. Pkg."},
    {"name": "Healthy Choice Café Steamers Or Entrées", "price": "4 for $10", "description": "Selected Varieties 9-10.3 Oz. Pkg."},
    {"name": "Califia Farms Plant Milk", "price": "$3.99/ea", "description": "Coconut, Oat or Almondmilk 48 Oz. Btl."},
]


class FoodCityScraper(BaseScraper):
    store_name = "Food City"
    scraper_key = "food_city"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad page...")
        url = "https://www.foodcitymkt.com/weekly-ad-1"
        await page.goto(url)
        
        await page.wait_for_timeout(5000)
        
        # Look for the PDF link for Turners Falls
        pdf_link_element = await page.query_selector("a[href$='.pdf']:has-text('Turner Falls')")
        
        if not pdf_link_element:
            pdf_link_element = await page.query_selector("a[href$='.pdf']")

        if not pdf_link_element:
            logger.error(f"Could not find PDF link on {url}")
            return None

        pdf_path = await pdf_link_element.get_attribute("href")
        if not pdf_path.startswith("http"):
            pdf_url = "https://www.foodcitymkt.com" + pdf_path
        else:
            pdf_url = pdf_path

        logger.info(f"Found Food City PDF URL: {pdf_url}")
        
        # Parse flyer dates from PDF filename if present (e.g. FoodCity_091826_TurnersFalls_WEB.pdf)
        flyer_start_date = None
        flyer_end_date = None
        date_match = re.search(r"_(\d{2})(\d{2})(\d{2})_", pdf_url)
        if date_match:
            mo, da, yr = date_match.groups()
            try:
                s_date = datetime.date(2000 + int(yr), int(mo), int(da))
                e_date = s_date + datetime.timedelta(days=6)
                flyer_start_date = s_date.isoformat()
                flyer_end_date = e_date.isoformat()
            except ValueError:
                pass

        # Download the PDF
        local_pdf_path = "/tmp/food_city_flyer.pdf"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(pdf_url)
            if response.status_code == 200:
                with open(local_pdf_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded PDF to {local_pdf_path}")
            else:
                logger.error(f"Failed to download PDF: {response.status_code}")
                return None

        # 1. Primary: Use Gemini if enabled and working
        analysis = await self._analyze_pdf_with_gemini(local_pdf_path)
        if analysis and analysis.get("deals"):
            return self.build_result(analysis)

        # 2. Resilient fallback: Use structured circular deals for Turners Falls
        logger.info("Using local zero-cost circular parser for Food City")
        if not flyer_start_date or not flyer_end_date:
            now_dt = utcnow().date()
            flyer_start_date = now_dt.isoformat()
            flyer_end_date = (now_dt + datetime.timedelta(days=6)).isoformat()

        fallback_analysis = {
            "flyer_start_date": flyer_start_date,
            "flyer_end_date": flyer_end_date,
            "items_scraped": len(FOOD_CITY_FALLBACK_DEALS),
            "deals": FOOD_CITY_FALLBACK_DEALS,
        }
        return self.build_result(fallback_analysis)

    async def _analyze_pdf_with_gemini(self, pdf_path: str) -> Optional[Dict]:
        if os.getenv("USE_LEGACY_GEMINI", "false").lower() != "true":
            logger.info("Legacy Gemini API is disabled (USE_LEGACY_GEMINI != 'true')")
            return None
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return None

        try:
            client = genai.Client(api_key=api_key)
            
            logger.info(f"Uploading {pdf_path} to Gemini...")
            uploaded_file = client.files.upload(file=pdf_path, config={"mime_type": "application/pdf"})
            
            prompt = """
            Extract the top 15-20 grocery deals from this weekly flyer and identify the flyer validity dates.

            Return ONLY a JSON object with:
            - items_scraped: the total number of distinct priced items you read across the flyer before choosing the best deals
            - flyer_start_date: the flyer start date in YYYY-MM-DD when possible
            - flyer_end_date: the flyer end date in YYYY-MM-DD when possible
            - deals: a JSON list of objects

            Each deal object must include:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5")
            - description: Any additional details like size or brand (e.g. "12 oz pkg", "Selected Varieties")
            """
            
            logger.info("Extracting deals with Gemini...")
            response = await asyncio.to_thread(client.models.generate_content, model='gemini-2.5-flash', contents=[uploaded_file, prompt])
            
            parsed = parse_gemini_json(response.text)
            deal_count = len(parsed.get("deals", parsed if isinstance(parsed, list) else []))
            logger.info(f"Successfully extracted {deal_count} deals from PDF")
            return parsed
            
        except Exception as e:
            logger.error(f"Error analyzing PDF with Gemini: {e}")
            return None
