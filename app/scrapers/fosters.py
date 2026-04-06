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

class FostersScraper(BaseScraper):
    store_name: str = "Foster's"

    async def scrape(self, page: Page) -> List[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad...")
        url = "https://www.fosterssupermarket.com/weekly-ad"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        # Look for the PDF link
        # Example from HTML: <a target="_blank" href="https://fosterssupermarketdata.shoptocook.com/shoptocook/Content/CircularPDF/01104/Fosters_040626_LR.pdf">View Printable PDF</a>
        pdf_link_element = await page.query_selector("a[href$='.pdf']")
        
        if not pdf_link_element:
            logger.error(f"Could not find PDF link on {url}")
            return []

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
            
            logger.info(f"Uploading {pdf_path} to Gemini for Foster's...")
            uploaded_file = genai.upload_file(path=pdf_path, mime_type="application/pdf")
            
            prompt = """
            Extract the top 15-20 grocery deals from this Foster's Supermarket weekly flyer.
            Look for dates to ensure it's for the current week (April 2026).
            For each deal, provide:
            - name: The name of the item
            - price: The sale price (e.g. "$1.99/lb", "2 for $5")
            - description: Any additional details like size or brand

            Return the data ONLY as a JSON list of objects.
            """
            
            logger.info("Extracting deals with Gemini for Foster's...")
            response = await asyncio.to_thread(model.generate_content, [uploaded_file, prompt])
            
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            deals = json.loads(text)
            logger.info(f"Successfully extracted {len(deals)} deals from Foster's PDF")
            return deals
            
        except Exception as e:
            logger.error(f"Error analyzing Foster's PDF with Gemini: {e}")
            return []
