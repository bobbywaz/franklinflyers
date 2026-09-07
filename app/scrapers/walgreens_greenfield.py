import logging
from typing import Any, Dict, List

from .pharmacy_base import PharmacyFlippScraper

logger = logging.getLogger(__name__)

WALGREENS_GREENFIELD_FALLBACKS: List[Dict[str, Any]] = [
    {
        "name": "Walgreens Brand Vitamins & Supplements",
        "price": "Buy 1 get 1 FREE with myWalgreens",
        "description": "Health & Beauty • Health Care | Select vitamins, gummies, and dietary supplements.",
    },
    {
        "name": "Pepperidge Farm Cookies 5.9-8.6 oz",
        "price": "2/ $8 with myWalgreens",
        "description": "Food, Beverages & Tobacco • Snacks | Milano, Chessmen, and Farmhouse favorites.",
    },
    {
        "name": "Red Bull Energy Drink 12 oz cans",
        "price": "3/ $8.50 with myWalgreens",
        "description": "Food, Beverages & Tobacco • Beverages | Regular or sugar-free energy drinks.",
    },
    {
        "name": "Excedrin Pain Relief Caplets 100 ct",
        "price": "$4 off 1 with myWalgreens",
        "description": "Health & Beauty • Health Care | Extra Strength or Migraine pain relief.",
    },
    {
        "name": "Vanity Fair Napkins or Scott Paper Towels",
        "price": "$1.50 off 2 with myWalgreens",
        "description": "Home & Garden • Household Supplies | Everyday household essentials.",
    },
    {
        "name": "Nice! Purified Water 24 pk., 16.9 oz bottles",
        "price": "2/ $6 with myWalgreens",
        "description": "Food, Beverages & Tobacco • Beverages | Refreshing clean bottled water.",
    },
    {
        "name": "Native Body Wash or Deodorant 2-Pack",
        "price": "$4 off 1 with myWalgreens",
        "description": "Health & Beauty • Personal Care | Naturally derived personal care products.",
    },
    {
        "name": "Systane or Pataday Eye Care Drops",
        "price": "$3 off 1 with myWalgreens",
        "description": "Health & Beauty • Health Care | Lubricant and allergy itch relief eye drops.",
    },
]


class WalgreensGreenfieldScraper(PharmacyFlippScraper):
    """Scraper for Walgreens located at 5 Pierce St, Greenfield, MA 01301.

    Extracts weekly circular promotional deals, discounts, and product categories
    from the Flipp circular API for ZIP code 01301.
    """
    store_name: str = "Walgreens (Greenfield)"
    scraper_key: str = "walgreens_greenfield"
    postal_code: str = "01301"
    flipp_search_query: str = "Walgreens"
    merchant_keyword: str = "walgreens"
    fallback_deals: List[Dict[str, Any]] = WALGREENS_GREENFIELD_FALLBACKS
