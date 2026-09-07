import datetime
from typing import Any, Dict
import pytest
from starlette.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.gemini_analyzer import (
    GeminiAnalyzer,
    PHARMACY_CATEGORIES,
    _categorize_pharmacy_item,
    _score_pharmacy_item,
)
from app.models import StoreDataset, StoreDeal
from app.scrapers.cvs_greenfield import CvsGreenfieldScraper
from app.scrapers.pharmacy_base import PharmacyFlippScraper
from app.scrapers.walgreens_greenfield import WalgreensGreenfieldScraper
from app.scrapers.walgreens_turners_falls import WalgreensTurnersFallsScraper
from app.store_utils import get_active_pharmacy_datasets, utcnow


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.mark.asyncio
async def test_cvs_greenfield_fallback():
    """Verify CVS Greenfield scraper fallback returns structured deals and dates."""
    scraper = CvsGreenfieldScraper()
    # Test scraping with a mock that returns empty items to trigger curated fallbacks
    scraper._fetch_flipp_items = lambda page=None: _async_return([])
    result = await scraper.scrape()

    assert result["scraper_key"] == "cvs_greenfield"
    assert result["store_name"] == "CVS Pharmacy (Greenfield)"
    assert result["kind"] == "pharmacy"
    assert len(result["deals"]) >= 5
    assert result["flyer_start_date"] is not None
    assert result["flyer_end_date"] is not None
    assert any("Water" in d["name"] or "Vitamins" in d["name"] for d in result["deals"])


@pytest.mark.asyncio
async def test_walgreens_greenfield_fallback():
    """Verify Walgreens Greenfield scraper fallback returns structured deals and dates."""
    scraper = WalgreensGreenfieldScraper()
    scraper._fetch_flipp_items = lambda page=None: _async_return([])
    result = await scraper.scrape()

    assert result["scraper_key"] == "walgreens_greenfield"
    assert result["store_name"] == "Walgreens (Greenfield)"
    assert result["kind"] == "pharmacy"
    assert len(result["deals"]) >= 5
    assert result["flyer_start_date"] is not None
    assert result["flyer_end_date"] is not None
    assert any("Vitamins" in d["name"] or "Cookies" in d["name"] for d in result["deals"])


@pytest.mark.asyncio
async def test_walgreens_turners_falls_fallback():
    """Verify Walgreens Turners Falls scraper fallback returns structured deals and dates."""
    scraper = WalgreensTurnersFallsScraper()
    scraper._fetch_flipp_items = lambda page=None: _async_return([])
    result = await scraper.scrape()

    assert result["scraper_key"] == "walgreens_turners_falls"
    assert result["store_name"] == "Walgreens (Turners Falls)"
    assert result["kind"] == "pharmacy"
    assert len(result["deals"]) >= 5
    assert result["flyer_start_date"] is not None
    assert result["flyer_end_date"] is not None
    assert any("Allergy" in d["name"] or "Glade" in d["name"] for d in result["deals"])


def test_pharmacy_price_formatting():
    """Verify price formatting logic handles numeric, fractional, and text discounts."""
    scraper = PharmacyFlippScraper()

    # Numeric price with pre/post text
    item1 = {
        "current_price": 7,
        "pre_price_text": "2/",
        "post_price_text": "with Card",
    }
    assert scraper._format_price(item1) == "2/ $7 with Card"

    # Float price
    item2 = {
        "current_price": 4.99,
        "pre_price_text": "",
        "post_price_text": "each",
    }
    assert scraper._format_price(item2) == "$4.99 each"

    # String price text
    item3 = {
        "current_price": None,
        "price_text": "Buy 1 Get 1 FREE",
    }
    assert scraper._format_price(item3) == "Buy 1 Get 1 FREE"

    # Sale story fallback
    item4 = {
        "current_price": None,
        "price_text": None,
        "sale_story": "$2 off 1 with coupon",
    }
    assert scraper._format_price(item4) == "$2 off 1 with coupon"


def test_pharmacy_description_formatting():
    """Verify description formatting combines category, text, and clipping image."""
    scraper = PharmacyFlippScraper()

    item = {
        "_L1": "Health & Beauty",
        "_L2": "Personal Care",
        "description": "Clean ingredient body wash",
        "sale_story": "Buy 1 get 1 50% off",
        "clipping_image_url": "https://f.wishabi.net/img.jpg",
    }
    desc = scraper._format_description(item, used_sale_story=False)
    assert "Health & Beauty • Personal Care" in desc
    assert "Clean ingredient body wash" in desc
    assert "Buy 1 get 1 50% off" in desc
    assert "Image: https://f.wishabi.net/img.jpg" in desc


def test_pharmacy_merchant_filtering():
    """Verify merchant keyword filtering isolates targeted pharmacy items."""
    scraper = CvsGreenfieldScraper()
    items = [
        {"name": "CVS Health Bandages", "merchant_name": "CVS Pharmacy"},
        {"name": "Walgreens Antacid", "merchant_name": "Walgreens"},
        {"name": "Target Shampoo", "merchant_name": "Target"},
    ]
    filtered = scraper._filter_merchant_items(items)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "CVS Health Bandages"


def test_get_active_pharmacy_datasets():
    """Verify get_active_pharmacy_datasets retrieves active datasets."""
    db = SessionLocal()
    try:
        now = utcnow()
        dataset = StoreDataset(
            scraper_key="test_cvs",
            store_name="CVS Pharmacy (Greenfield)",
            kind="pharmacy",
            trigger_mode="manual_test",
            status="success",
            started_at=now,

            finished_at=now,
            expires_at=now + datetime.timedelta(days=3),
            item_count=1,
            items_scraped_count=1,
        )
        db.add(dataset)
        db.flush()

        deal = StoreDeal(
            dataset_id=dataset.id,
            item_name="Purified Water 24 pk",
            sale_price="2/ $7",
            description="Beverages",
        )
        db.add(deal)
        db.commit()

        active = get_active_pharmacy_datasets(db, now=now)
        keys = [d.scraper_key for d in active]
        assert "test_cvs" in keys

        # Clean up test dataset
        db.delete(deal)
        db.delete(dataset)
        db.commit()
    finally:
        db.close()


def test_pharmacies_route_html():
    """Verify /pharmacies endpoint renders 200 OK with expected markup and navigation."""
    client = TestClient(app)
    response = client.get("/pharmacies")
    assert response.status_code == 200
    html = response.text
    assert "Franklin County Pharmacies" in html
    assert "137 Federal Street" not in html
    assert "5 Pierce Street" not in html
    assert "240 Avenue A" not in html
    assert "Current Pharmacy Circulars" in html
    assert "https://www.cvs.com/weeklyad" in html
    assert "https://www.walgreens.com/offers/offers.jsp" in html
    assert "/pharmacies" in html


def test_categorize_pharmacy_item():
    """Verify pharmacy items are categorized correctly into 6 standardized departments."""
    assert _categorize_pharmacy_item("Nature Made Super B-Complex", "Vitamins & Supplements") == "Vitamins & Supplements"
    assert _categorize_pharmacy_item("Centrum Adult Multivitamin", "") == "Vitamins & Supplements"
    assert _categorize_pharmacy_item("Advil Targeted Relief Cream", "Pain Relief") == "Health & Medicine"
    assert _categorize_pharmacy_item("Claritin 24 Hour Allergy Tablets", "Health Care") == "Health & Medicine"
    assert _categorize_pharmacy_item("Colgate Optic White Toothpaste", "Oral Care") == "Personal Care & Beauty"
    assert _categorize_pharmacy_item("Native Body Wash", "Personal Care") == "Personal Care & Beauty"
    assert _categorize_pharmacy_item("Walgreens Trash Bags", "Household Supplies") == "Household & Paper Goods"
    assert _categorize_pharmacy_item("Bounty Paper Towels", "Paper Products") == "Household & Paper Goods"
    assert _categorize_pharmacy_item("12-Pack Pepsi Products", "Beverages") == "Snacks & Beverages"
    assert _categorize_pharmacy_item("Lindt Premium Chocolate Bars", "Food Items") == "Snacks & Beverages"
    assert _categorize_pharmacy_item("WaterWipes Baby Wipes", "Diapering") == "Baby & Family"
    assert _categorize_pharmacy_item("Huggies Diapers Jumbo Pack", "Baby & Toddler") == "Baby & Family"


def test_score_pharmacy_item():
    """Verify pharmacy deals receive realistic scores and rationale on a 1-10 scale."""
    # Volume deals (10/10)
    score1, exp1 = _score_pharmacy_item("Walgreens Trash Bags", "Buy 1 get 2 FREE")
    assert score1 == 10
    assert "volume savings" in exp1.lower()

    # BOGO Free (9/10)
    score2, exp2 = _score_pharmacy_item("Nature Made Vitamins", "Buy 1 get 1 FREE")
    assert score2 == 9

    # Straight 50% off (9/10)
    score3, exp3 = _score_pharmacy_item("Photo Enlargement", "50% off")
    assert score3 == 9

    # High coupon value $10+ (9/10)
    score4, exp4 = _score_pharmacy_item("Colgate Toothpaste", "$11 off 2 online coupon")
    assert score4 == 9

    # Reward threshold $10 on $30 (8 or 9/10)
    score5, exp5 = _score_pharmacy_item("Diapers", "Spend $30 get $10 ExtraBucks")
    assert score5 in (8, 9)

    # Moderate coupon $4 off (8/10)
    score6, exp6 = _score_pharmacy_item("Advil", "$4 off 1")
    assert score6 == 8

    # BOGO 50% off (7/10)
    score7, exp7 = _score_pharmacy_item("Native Body Wash", "Buy 1 get 1 50% OFF")
    assert score7 == 7

    # Standard coupon $1 off (6/10)
    score8, exp8 = _score_pharmacy_item("Q-Tips", "$1 off 1")
    assert score8 == 6


@pytest.mark.asyncio
async def test_analyze_pharmacy_deals_mock():
    """Verify GeminiAnalyzer._mock_analyze_pharmacy organizes deals into departments and picks winner."""
    analyzer = GeminiAnalyzer()
    sample_deals = [
        {
            "id": 1,
            "store_name": "Walgreens (Greenfield)",
            "scraper_key": "walgreens_greenfield",
            "town": "Greenfield",
            "name": "Walgreens Trash Bags",
            "price": "Buy 1 get 2 FREE",
            "description": "Household Supplies",
        },
        {
            "id": 2,
            "store_name": "CVS Pharmacy (Greenfield)",
            "scraper_key": "cvs_greenfield",
            "town": "Greenfield",
            "name": "Nature Made Multivitamins",
            "price": "Buy 1 get 1 FREE",
            "description": "Vitamins & Supplements",
        },
        {
            "id": 3,
            "store_name": "Walgreens (Turners Falls)",
            "scraper_key": "walgreens_turners_falls",
            "town": "Turners Falls",
            "name": "Pepsi 12-Pack",
            "price": "Buy 2 get 2 FREE",
            "description": "Beverages",
        },
    ]

    result = await analyzer.analyze_pharmacy_deals(sample_deals)
    assert "scored_deals" in result
    assert "top_overall" in result
    assert "deals_by_category" in result
    assert "best_pharmacy" in result

    assert len(result["top_overall"]) >= 2
    assert result["best_pharmacy"]["score"] >= 8
    assert all(cat in result["deals_by_category"] for cat in PHARMACY_CATEGORIES)


def test_pharmacies_route_ai_sections():
    """Verify /pharmacies renders AI top deals, department sections, and best store value summary."""
    client = TestClient(app)
    response = client.get("/pharmacies")
    assert response.status_code == 200
    html = response.text

    assert "Top Pharmacy Deals Overall" in html
    assert "Top Deals by Department" in html
    assert "Best Pharmacy Value This Week" in html
    assert "Search &amp; Browse All Circular Deals" in html or "Search & Browse All Circular Deals" in html
    assert "Score: " in html
    assert "Filter by Department:" in html
    assert "Filter by Store:" in html

    # Top Pharmacy Deals Overall structure checks
    if "<span>Top Pharmacy Deals Overall</span>" in html:
        top_section = html.split("<span>Top Pharmacy Deals Overall</span>")[1].split("Top Deals by Department")[0]
        assert 'title="View store ad"' in top_section
        assert "Store Ad ↗" not in top_section
        assert "text-lg text-gray-900" in top_section
        assert "text-sm font-semibold text-emerald-700" in top_section
        assert "truncate max-w-[120px]" not in top_section
        assert "bg-gray-100 p-2.5 rounded-lg border" not in top_section


async def _async_return(val):
    return val

