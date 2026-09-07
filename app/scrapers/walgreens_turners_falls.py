import logging
from typing import Any, Dict, List

from .pharmacy_base import PharmacyFlippScraper

logger = logging.getLogger(__name__)

WALGREENS_TURNERS_FALLS_FALLBACKS: List[Dict[str, Any]] = [
    {
        "name": "Walgreens Brand Allergy & Cold Relief",
        "price": "Buy 1 get 1 50% OFF with myWalgreens",
        "description": "Health & Beauty • Health Care | Wal-itin, Wal-Zyr, and multi-symptom cold caplets.",
    },
    {
        "name": "Glade Aerosol Scent Sprays 8 oz",
        "price": "$1.59 with myWalgreens",
        "description": "Home & Garden • Household Supplies | Clean linen, lavender, and Hawaiian breeze scents.",
    },
    {
        "name": "Nature's Bounty Vitamins & Supplements",
        "price": "Buy 1 get 1 FREE with myWalgreens",
        "description": "Health & Beauty • Health Care | Hair, skin & nails gummies, fish oil, and vitamin D3.",
    },
    {
        "name": "Doritos or Lay's Potato Chips",
        "price": "Buy 2 get 1 FREE with myWalgreens",
        "description": "Food, Beverages & Tobacco • Snacks | Classic potato chips and tortilla snack bags.",
    },
    {
        "name": "Bounty Essentials Paper Towels 6 rolls",
        "price": "$5.99 with myWalgreens",
        "description": "Home & Garden • Household Supplies | Strong and absorbent kitchen paper rolls.",
    },
    {
        "name": "Colgate Total or Optic White Toothpaste",
        "price": "$4.00 with myWalgreens",
        "description": "Health & Beauty • Personal Care | Oral care whitening and cavity protection.",
    },
    {
        "name": "Systane Zaditor Eye Itch Relief Drops 0.17 oz",
        "price": "$3 off 1 with myWalgreens",
        "description": "Health & Beauty • Health Care | Fast-acting 12-hour antihistamine eye drops.",
    },
    {
        "name": "WaterWipes or Huggies Baby Wipes 3-Pack",
        "price": "$3 off 2 with myWalgreens",
        "description": "Baby & Toddler • Diapering | Sensitive skin chemical-free pure water wipes.",
    },
]


class WalgreensTurnersFallsScraper(PharmacyFlippScraper):
    """Scraper for Walgreens located at 240 Avenue A, Turners Falls, MA 01376.

    Extracts weekly circular promotional deals, discounts, and product categories
    from the Flipp circular API for ZIP code 01376.
    """
    store_name: str = "Walgreens (Turners Falls)"
    scraper_key: str = "walgreens_turners_falls"
    postal_code: str = "01376"
    flipp_search_query: str = "Walgreens"
    merchant_keyword: str = "walgreens"
    fallback_deals: List[Dict[str, Any]] = WALGREENS_TURNERS_FALLS_FALLBACKS
