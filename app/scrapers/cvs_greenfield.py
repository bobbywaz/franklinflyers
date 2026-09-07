import logging
from typing import Any, Dict, List

from .pharmacy_base import PharmacyFlippScraper

logger = logging.getLogger(__name__)

CVS_GREENFIELD_FALLBACKS: List[Dict[str, Any]] = [
    {
        "name": "Well Market or Gold Emblem purified water 24 pk., 16.9 oz bottles",
        "price": "2/ $7 WITH CARD",
        "description": "Food, Beverages & Tobacco • Beverages | Quality purified drinking water.",
    },
    {
        "name": "CVS Health & Nature Made Vitamins and Supplements",
        "price": "Buy 1 get 1 FREE WITH CARD",
        "description": "Health & Beauty • Health Care | Full line of multivitamins, letter vitamins, and herbal supplements.",
    },
    {
        "name": "Dunkin' Bagged Coffee 11-12 oz or K-Cups 10 ct",
        "price": "$7.99 WITH CARD",
        "description": "Food, Beverages & Tobacco • Beverages | Original blend, dark roast, and seasonal roasts.",
    },
    {
        "name": "Huggies Diapers, Pull-Ups, Goodnites or Wipes",
        "price": "Buy 1 get 1 50% OFF WITH CARD",
        "description": "Baby & Toddler • Diapering | Also get savings with digital coupons.",
    },
    {
        "name": "Total Home Paper Towels 6 rolls or Bath Tissue 12 rolls",
        "price": "Buy 1 get 1 50% OFF WITH CARD",
        "description": "Home & Garden • Household Supplies | Absorbent household paper products.",
    },
    {
        "name": "Adult Flonase or Sensimist Allergy Relief",
        "price": "$4 off 1 WITH CARD",
        "description": "Health & Beauty • Health Care | 24-hour non-drowsy allergy relief sprays.",
    },
    {
        "name": "Native Body Wash or Deodorant",
        "price": "Buy 1 get 1 50% OFF WITH CARD",
        "description": "Health & Beauty • Personal Care | Clean ingredient body care and aluminum-free deodorant.",
    },
    {
        "name": "Hershey's, Mars or M&M's Share Size Candy",
        "price": "2/ $6 WITH CARD",
        "description": "Food, Beverages & Tobacco • Snacks | Assorted chocolates and sweet treats.",
    },
]


class CvsGreenfieldScraper(PharmacyFlippScraper):
    """Scraper for CVS Pharmacy located at 137 Federal St, Greenfield, MA 01301.

    Extracts weekly circular promotional deals, discounts, and product categories
    from the Flipp circular API for ZIP code 01301.
    """
    store_name: str = "CVS Pharmacy (Greenfield)"
    scraper_key: str = "cvs_greenfield"
    postal_code: str = "01301"
    flipp_search_query: str = "CVS"
    merchant_keyword: str = "cvs"
    fallback_deals: List[Dict[str, Any]] = CVS_GREENFIELD_FALLBACKS
