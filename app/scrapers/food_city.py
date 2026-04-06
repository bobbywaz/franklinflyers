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

class FoodCityScraper(BaseScraper):
    store_name = "Food City"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad page...")
        # The user pointed out this specific URL for Turners Falls
        url = "https://www.foodcitymkt.com/weekly-ad-1"
        await page.goto(url)
        
        await page.wait_for_timeout(5000)
        
        # Look for the PDF link for Turners Falls
        # In the HTML we saw: <a href="/s/FoodCity_040326_TurnersFalls_WEB.pdf" ...>Turner Falls, MA</a>
        pdf_link_element = await page.query_selector("a[href$='.pdf']:has-text('Turner Falls')")
        
        if not pdf_link_element:
            # Fallback to any PDF link if the specific one isn't found
            pdf_link_element = await page.query_selector("a[href$='.pdf']")

        if not pdf_link_element:
            logger.error(f"Could not find PDF link on {url}")
            return []

        pdf_path = await pdf_link_element.get_attribute("href")
        if not pdf_path.startswith("http"):
            pdf_url = "https://www.foodcitymkt.com" + pdf_path
        else:
            pdf_url = pdf_path

        logger.info(f"Found Food City PDF URL: {pdf_url}")
        
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
                return []

        # Use Gemini to extract deals from the PDF
        deals = await self._analyze_pdf_with_gemini(local_pdf_path)
        return deals

    async def _analyze_pdf_with_gemini(self, pdf_path: str) -> List[Dict]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return []

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Upload the file to Gemini API
            logger.info(f"Uploading {pdf_path} to Gemini...")
            uploaded_file = genai.upload_file(path=pdf_path, mime_type="application/pdf")
            
            prompt = """
            Extract the top 15-20 grocery deals from this weekly flyer.
            For each deal, provide:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5")
            - description: Any additional details like size or brand (e.g. "12 oz pkg", "Selected Varieties")

            Return the data ONLY as a JSON list of objects.
            Example format:
            [
              {"name": "Apple", "price": "$0.99/lb", "description": "Gala or Fuji"},
              {"name": "Milk", "price": "$3.49", "description": "1 Gallon"}
            ]
            """
            
            logger.info("Extracting deals with Gemini...")
            response = await asyncio.to_thread(model.generate_content, [uploaded_file, prompt])
            
            # Clean up uploaded file from Gemini (optional but good practice)
            # genai.delete_file(uploaded_file.name)
            
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            deals = json.loads(text.strip())
            logger.info(f"Successfully extracted {len(deals)} deals from PDF")
            return deals
            
        except Exception as e:
            logger.error(f"Error analyzing PDF with Gemini: {e}")
            return []
