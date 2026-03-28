import os
import json
import logging
from typing import List, Dict
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def analyze_deals(self, all_deals: List[Dict]) -> Dict:
        """
        Analyze a list of deals from all stores and return scored deals and a best store recommendation.
        """
        if not all_deals:
            return {"scored_deals": [], "best_store": None}

        # Format deals for the prompt
        deals_text = "\n".join([
            f"Store: {d['store_name']} | Item: {d['name']} | Price: {d['price']} | Desc: {d.get('description', '')}"
            for d in all_deals
        ])

        prompt = f"""
        You are an expert grocery shopper analyzing weekly flyer deals for Greenfield, MA.
        Evaluate these deals based on value, price history trends, and quality.

        Deals to analyze:
        {deals_text}

        Return a JSON object with:
        1. 'scored_deals': A list of the best deals (up to 20). Each deal must include:
           'store_name', 'item_name', 'sale_price', 'category' (meat, dairy, produce, pantry, etc.), 
           'score' (1-10), 'explanation' (why it's a good/bad deal).
        2. 'best_store': An object with:
           'store_name', 'summary' (overall view of this week's value), 
           'strengths', 'weaknesses', 'score' (1-10).

        Be critical! Don't just give 10s. If a price is standard, give it a 5. If it's a fake sale, give it lower.
        Respond ONLY with JSON.
        """

        try:
            response = self.model.generate_content(prompt)
            # Remove markdown code block if present
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text.strip())
            return result
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {"scored_deals": [], "best_store": None}
