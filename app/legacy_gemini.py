"""Legacy Gemini API Integration (Archived).

This module preserves all legacy Google GenAI API calls, prompts, and schemas previously
used for grocery flyer extraction, deal scoring, recipe generation, and pharmacy circular analysis.

Franklin Flyers has migrated to $0-cost deterministic rule-based curation and host
Antigravity (agy) automation. This code is kept safely intact for historical reference
and can be re-enabled if desired by setting USE_LEGACY_GEMINI=true and GEMINI_API_KEY.
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy import of google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def parse_gemini_json(text: str):
    """Clean markdown code fences from Gemini responses and parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


async def analyze_pdf_with_gemini(pdf_path: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """Legacy: Upload a weekly grocery flyer PDF (Food City, Foster's) to Gemini 2.5 Flash."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None

    if genai is None:
        logger.error("google-genai package is not installed")
        return None

    try:
        client = genai.Client(api_key=api_key)
        logger.info("Uploading %s to Gemini...", pdf_path)
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
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
        )

        parsed = parse_gemini_json(response.text)
        deal_count = len(parsed.get("deals", parsed if isinstance(parsed, list) else []))
        logger.info("Successfully extracted %s deals from PDF via legacy Gemini", deal_count)
        return parsed
    except Exception as e:
        logger.error("Error analyzing PDF with legacy Gemini: %s", e)
        return None


async def analyze_screenshot_with_gemini(image_path: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """Legacy: Analyze an ALDI weekly ad screenshot with Gemini 2.5 Flash."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set")
        return None

    if genai is None:
        logger.error("google-genai package is not installed")
        return None

    try:
        client = genai.Client(api_key=api_key)
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_parts = [
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png",
            )
        ]

        prompt = """
        Analyze this weekly grocery ad circular (ALDI) and extract the top deals.
        Also determine the validity dates of the flyer if visible (start date and end date).

        Return ONLY a JSON object with:
        - items_scraped: the total number of distinct priced items visible on the ad
        - flyer_start_date: the start date in YYYY-MM-DD format (or null if not found)
        - flyer_end_date: the end date in YYYY-MM-DD format (or null if not found)
        - deals: a list of deal objects

        Each deal object must include:
        - name: The name of the item
        - price: The sale price
        - description: Any additional details (size, variety, etc.)
        """

        logger.info("Extracting ALDI deals from screenshot with legacy Gemini...")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[prompt, image_parts[0]],
        )

        parsed = parse_gemini_json(response.text)
        return parsed
    except Exception as e:
        logger.error("Error analyzing ALDI screenshot with legacy Gemini: %s", e)
        return None


async def analyze_grocery_deals_gemini(deals: List[Dict], api_key: Optional[str] = None) -> Dict:
    """Legacy: Analyze and score grocery deals across all local supermarkets using Gemini 2.5 Flash."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return {"scored_deals": [], "best_store": None}

    client = genai.Client(api_key=api_key)
    deals_json = json.dumps(deals)

    prompt = f"""
    You are an expert grocery bargain hunter and meal planner.
    Analyze the following list of grocery deals from multiple stores in Greenfield, MA:
    {deals_json}

    Tasks:
    1. Score each deal from 1 to 10 based on how good of a discount it is (10 being an incredible loss-leader).
    2. Categorize each deal into one of: Produce, Meat & Seafood, Dairy, Bakery, Pantry, Frozen, Household.
    3. Filter down to the top genuine high-value deals.
    4. Pick the "Best Store of the Week" based on overall value.

    Return ONLY a JSON object with:
    - scored_deals: list of objects with (store_name, item_name, sale_price, category, score, explanation)
    - best_store: object with (store_name, summary, strengths, weaknesses, score)
    """

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return parse_gemini_json(response.text)
    except Exception as e:
        logger.error("Error calling legacy Gemini API for grocery deals: %s", e)
        return {"scored_deals": [], "best_store": None}


async def generate_recipe_gemini(scored_deals: List[Dict], api_key: Optional[str] = None) -> Dict:
    """Legacy: Generate a budget family recipe from scored deals using Gemini 2.5 Flash."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return {}

    client = genai.Client(api_key=api_key)
    top_deals = [d for d in scored_deals if d.get("score", 0) >= 8][:10]
    deals_summary = json.dumps([{"name": d.get("item_name", d.get("name")), "price": d.get("sale_price", d.get("price")), "store": d.get("store_name")} for d in top_deals])

    prompt = f"""
    You are a resourceful home cook and meal-planning assistant for Franklin Flyers.
    Create ONE practical, delicious, budget-friendly family recipe (serves 4) using at least 1-2 featured sale items.

    Featured deals:
    {deals_summary}

    Return ONLY a JSON object with:
    - recipe_name
    - ingredients_from_deals (list of strings with price and store)
    - other_ingredients (common kitchen staples)
    - instructions (concise step-by-step)
    - cost_per_plate (e.g. "$2.50 per plate")
    """

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return parse_gemini_json(response.text)
    except Exception as e:
        logger.error("Error calling legacy Gemini API for recipe: %s", e)
        return {}


async def analyze_pharmacy_deals_gemini(all_deals: List[Dict], api_key: Optional[str] = None) -> Dict:
    """Legacy: Evaluate weekly pharmacy circular promotions using Gemini 2.5 Flash."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return {"scored_deals": [], "best_pharmacy": None}

    client = genai.Client(api_key=api_key)
    deals_json = json.dumps(all_deals[:25], indent=2)

    prompt = f"""
    You are an expert budget shopper analyzing weekly pharmacy circular promotions for Greenfield and Turners Falls, MA (CVS Pharmacy and Walgreens).
    Evaluate these top promotional deals based on real value, discount depth, and household necessity:
    {deals_json}

    Return a JSON object with:
    1. 'scored_deals': evaluated deals with name, store_name, price, category, score (1-10), explanation
    2. 'best_pharmacy': object with store_name, summary, strengths, weaknesses, score
    """

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return parse_gemini_json(response.text)
    except Exception as e:
        logger.error("Error calling legacy Gemini API for pharmacy analysis: %s", e)
        return {"scored_deals": [], "best_pharmacy": None}
