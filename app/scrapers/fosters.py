import logging
import httpx
import os
import json
import asyncio
from google import genai
from .base import BaseScraper
from typing import Dict, Optional
from playwright.async_api import Page
from ..store_utils import parse_gemini_json

logger = logging.getLogger(__name__)

class FostersScraper(BaseScraper):
    store_name: str = "Foster's"
    scraper_key: str = "fosters"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad...")
        url = "https://www.fosterssupermarket.com/weekly-ad/"
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        
        # Look for the PDF link
        # Example from HTML: <a target="_blank" href="https://fosterssupermarketdata.shoptocook.com/shoptocook/Content/CircularPDF/01104/Fosters_040626_LR.pdf">View Printable PDF</a>
        pdf_link_element = await page.query_selector("a[href$='.pdf']")
        
        if not pdf_link_element:
            logger.error(f"Could not find PDF link on {url}")
            return None

        pdf_url = await pdf_link_element.get_attribute("href")
        logger.info(f"Found Foster's PDF URL: {pdf_url}")
        
        # Download the PDF
        local_pdf_path = "/tmp/fosters_flyer.pdf"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(pdf_url)
            if response.status_code == 200:
                with open(local_pdf_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded Foster's PDF to {local_pdf_path}")
            else:
                logger.error(f"Failed to download Foster's PDF: {response.status_code}")
                return None

        # Use Gemini to extract deals from the PDF
        analysis = await self._analyze_pdf_with_gemini(local_pdf_path)
        if analysis is None:
            return None
        return self.build_result(analysis)

    async def _analyze_pdf_with_gemini(self, pdf_path: str) -> Optional[Dict]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return None

        try:
            client = genai.Client(api_key=api_key)
            pass  # model instantiation removed
            
            logger.info(f"Uploading {pdf_path} to Gemini for Foster's...")
            uploaded_file = client.files.upload(file=pdf_path, config={"mime_type": "application/pdf"})
            
            prompt = """
            Extract the top 15-20 grocery deals from this Foster's Supermarket weekly flyer and identify the flyer validity dates.

            Return ONLY a JSON object with:
            - items_scraped: the total number of distinct priced items you read across the flyer before choosing the best deals
            - flyer_start_date: the flyer start date in YYYY-MM-DD when possible
            - flyer_end_date: the flyer end date in YYYY-MM-DD when possible
            - deals: a JSON list of objects

            Each deal object must include:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5")
            - description: Any additional details like size or brand
            """
            
            logger.info("Extracting deals with Gemini for Foster's...")
            response = await asyncio.to_thread(client.models.generate_content, model='gemini-2.5-flash', contents=[uploaded_file, prompt])
            
            parsed = parse_gemini_json(response.text)
            deal_count = len(parsed.get("deals", parsed if isinstance(parsed, list) else []))
            logger.info(f"Successfully extracted {deal_count} deals from Foster's PDF")
            return parsed
            
        except Exception as e:
            logger.error(f"Error analyzing Foster's PDF with Gemini: {e}")
            return None
