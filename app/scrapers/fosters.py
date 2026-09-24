import logging
import httpx
import os
import json
import asyncio
import zlib
import re
import datetime
from google import genai
from .base import BaseScraper
from typing import Dict, Optional, List
from playwright.async_api import Page
from ..store_utils import parse_gemini_json, utcnow

logger = logging.getLogger(__name__)


def _clean_pdf_token(val: str) -> str:
    text_parts = re.findall(r"\((.*?)\)", val)
    res = ""
    for p in text_parts:
        p = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), p)
        p = p.replace(r"\(", "(").replace(r"\)", ")")
        res += p
    res = res.replace("\x1f", "fi").replace("\x1e", "fl")
    res = res.replace("\x92", "'").replace("\x91", "'").replace("\x93", '"').replace("\x94", '"').replace("\x95", "•")
    res = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", res)
    return res.strip()


def _clean_product_name(name: str) -> str:
    patterns = [
        r"^(?:Tender & Juicy|Crisp & Crunchy|Sweet & Delicious|Meaty & Delicious|Savory & Juicy|Rich & Savory|Rich & Smooth|Old World Flavor|Mild & Creamy|Mild & Delicate|Mild & Tender|Rich & Firm|Sweet & Tropical|Spicy & Tart|Sweet & Juicy|Warm & Golden|Earthy & Robust|Decadent)\s+",
        r"\s+(?:Fresh|Frozen|Buy in Bulk)$",
    ]
    for p in patterns:
        name = re.sub(p, "", name, flags=re.IGNORECASE).strip()
    return name


class FostersScraper(BaseScraper):
    store_name: str = "Foster's"
    scraper_key: str = "fosters"

    async def scrape(self, page: Page) -> Optional[Dict]:
        logger.info(f"Navigating to {self.store_name} weekly ad...")
        url = "https://www.fosterssupermarket.com/weekly-ad/"
        await page.goto(url, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        
        # Look for the PDF link
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

        # 1. Primary: Extract deals locally directly from the InDesign vector PDF
        analysis = self._extract_deals_from_pdf(local_pdf_path, pdf_url=pdf_url)
        if analysis and analysis.get("deals"):
            logger.info("Successfully extracted %s deals locally from Foster's PDF", len(analysis["deals"]))
            return self.build_result(analysis)

        # 2. Secondary fallback: Gemini API if configured
        analysis = await self._analyze_pdf_with_gemini(local_pdf_path)
        if analysis and analysis.get("deals"):
            return self.build_result(analysis)

        return None

    def _extract_deals_from_pdf(self, pdf_path: str, pdf_url: str = "") -> Optional[Dict]:
        try:
            with open(pdf_path, "rb") as f:
                content = f.read()

            streams = re.findall(rb"stream[\r\n]+([\s\S]*?)[\r\n]+endstream", content)
            items = []
            for s in streams:
                try:
                    decomp = zlib.decompress(s).decode("latin1")
                    if "BT" not in decomp:
                        continue
                    ops = re.findall(r"(\[.*?\]\s*TJ|\(.*?\)\s*Tj)", decomp)
                    for op in ops:
                        txt = _clean_pdf_token(op)
                        if txt:
                            items.append(txt)
                except Exception:
                    pass

            flyer_start = None
            flyer_end = None
            for i, t in enumerate(items):
                if "Sale Date" in t:
                    date_str = items[i + 1] if i + 1 < len(items) else ""
                    m = re.search(r"([A-Za-z]+)\.?\s*(\d{1,2})\s*-\s*([A-Za-z]+)\.?\s*(\d{1,2}),?\s*(\d{4})", date_str)
                    if m:
                        m1, d1, m2, d2, y = m.groups()
                        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
                        flyer_start = f"{y}-{months[m1.lower()[:3]]:02d}-{int(d1):02d}"
                        flyer_end = f"{y}-{months[m2.lower()[:3]]:02d}-{int(d2):02d}"
                    break

            if not flyer_start and pdf_url:
                url_match = re.search(r"_(\d{2})(\d{2})(\d{2})_", pdf_url)
                if url_match:
                    mo, da, yr = url_match.groups()
                    s_date = datetime.date(2000 + int(yr), int(mo), int(da))
                    e_date = s_date + datetime.timedelta(days=5)
                    flyer_start = s_date.isoformat()
                    flyer_end = e_date.isoformat()

            ignore_tokens = {
                "WE ARE OPEN FROM 7am to 7pm", "6 DAYS A WEEK • CLOSED SUNDAYS",
                "Have you heard?", "Details on pg. 8", "Have our specials emailed to you every week",
                "See back page for details.", "Sale Dates:", "Corner", "Cornershop",
            }

            deals = []
            i = 0
            while i < len(items):
                t = items[i]
                price = None
                unit = ""
                consumed = 0

                if i + 1 < len(items) and items[i] in ("2/$", "3/$", "4/$", "5/$", "10/$"):
                    price = f"{items[i]}{items[i+1]}"
                    consumed = 2
                elif i + 1 < len(items) and items[i].isdigit() and len(items[i]) <= 2 and items[i+1].isdigit() and len(items[i+1]) == 2:
                    price = f"${items[i]}.{items[i+1]}"
                    consumed = 2
                    if i + 2 < len(items) and items[i+2] in ("Lb.", "Ea.", "Lb", "Ea"):
                        unit = f"/{items[i+2]}"
                        consumed = 3
                elif i + 1 < len(items) and items[i].isdigit() and items[i+1] == "¢":
                    price = f"{items[i]}¢"
                    consumed = 2
                    if i + 2 < len(items) and items[i+2] in ("Lb.", "Ea.", "Lb", "Ea"):
                        unit = f"/{items[i+2]}"
                        consumed = 3

                if price:
                    full_price = f"{price}{unit}"
                    lookback = []
                    k = i - 1
                    while k >= 0 and (i - k) <= 6:
                        prev = items[k]
                        if prev in ignore_tokens or prev.startswith("Page ") or prev.isdigit() or prev in ("Lb.", "Ea.", "¢", "2/$", "3/$", "4/$"):
                            break
                        lookback.insert(0, prev)
                        k -= 1

                    name_parts = []
                    desc_parts = []
                    for part in lookback:
                        if any(x in part for x in ["Oz.", "Pack", "Varieties", "Pan", "Ct.", "Sliced", "Bone-In", "Choice", "Angus", "Fresh In-Store", "Assorted", "Bagged", "Fresh", "Frozen", "Buy in Bulk"]):
                            desc_parts.append(part)
                        else:
                            name_parts.append(part)

                    if name_parts:
                        raw_name = " ".join(name_parts).strip()
                        item_name = _clean_product_name(raw_name)
                        desc = " ".join(desc_parts).strip()
                        if len(item_name) > 2 and not item_name.isdigit():
                            deals.append({"name": item_name, "price": full_price, "description": desc})

                    i += consumed
                else:
                    i += 1

            seen = set()
            unique_deals = []
            for d in deals:
                if d["name"] not in seen:
                    seen.add(d["name"])
                    unique_deals.append(d)

            if unique_deals:
                return {
                    "flyer_start_date": flyer_start,
                    "flyer_end_date": flyer_end,
                    "items_scraped": len(unique_deals),
                    "deals": unique_deals[:30],
                }
            return None
        except Exception as e:
            logger.error(f"Error parsing Foster's PDF text: {e}")
            return None

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
            logger.info(f"Successfully extracted {deal_count} deals from Foster's PDF with Gemini")
            return parsed
            
        except Exception as e:
            logger.error(f"Error analyzing Foster's PDF with Gemini: {e}")
            return None
