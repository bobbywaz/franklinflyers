import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.scrapers.patriot_care import PatriotCareScraper
from app.scrapers.rise_dispensary import RiseDispensaryScraper
from app.scrapers.leaf_joy import LeafJoyScraper
from app.scrapers.heirloom_collection import HeirloomCollectionScraper
from app.scrapers.pharmacy_257 import Pharmacy257Scraper
from app.scrapers.smokey_leaf import SmokeyLeafScraper
from app.scrapers.cheech_and_chong import CheechAndChongScraper
from app.main import app, get_discount_percentage, score_weed_deal, categorize_weed
from app.models import StoreDataset, StoreDeal
from app.store_utils import utcnow


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_get_discount_percentage_and_scoring():
    """Verify discount parsing handles BOGO, percentage off, sale from text, and zero for regular items."""
    # BOGO
    d_bogo = get_discount_percentage("Gummies BOGO Free", "Buy 1 Get 1 Free promotion", "$25.00")
    assert d_bogo == 0.50
    assert score_weed_deal(d_bogo) == 10

    # 30% off text
    d_pct = get_discount_percentage("Cartridge Special", "Take 30% off selected carts today", "$30.00")
    assert d_pct == 0.30
    assert score_weed_deal(d_pct) == 9

    # Sale from $X with price $Y
    d_sale = get_discount_percentage("Wedding Cake 3.5g", "Hybrid | Sale from $40.00", "$28.00")
    assert abs(d_sale - 0.30) < 0.01
    assert score_weed_deal(d_sale) == 9

    # Moderate discount 22%
    d_mod = get_discount_percentage("Brownie Scout", "Indica | Sale from $45.00", "$35.00")
    assert abs(d_mod - 0.222) < 0.01
    assert score_weed_deal(d_mod) == 8

    # Regular menu item with no discount mentioned
    d_reg = get_discount_percentage("Grandpa's Cookies 1g", "Hybrid | 20.4% THC | Earthy pine", "$9.00")
    assert d_reg == 0.0
    assert score_weed_deal(d_reg) == 1


def test_categorize_weed():
    """Verify cannabis categorization logic."""
    assert categorize_weed("Wedding Cake Flower 3.5g", "Fresh buds") == "Flower"
    assert categorize_weed("French King Pre-Rolls", "5-pack joint tin") == "Pre-rolls"
    assert categorize_weed("Wild Berry Gummies", "100mg THC edible chew") == "Edibles"
    assert categorize_weed("Gelato Cartridge", "0.5g vape pen") == "Vapes"
    assert categorize_weed("Live Resin Sugar", "Concentrate 1g Chem Dog") == "Concentrates"


def test_dispensaries_route_uncapped_and_zero_filler():
    """Verify /dispensaries renders genuine deals uncapped without score <= 6 filler items."""
    db = SessionLocal()

    # Add a mock dataset and some deals
    dataset = StoreDataset(
        scraper_key="patriot_care",
        store_name="Patriot Care",
        kind="dispensary",
        items_scraped_count=2,
        status="success",
        trigger_mode="manual_single",
        flyer_start_date=utcnow().date(),
        flyer_end_date=utcnow().date() + datetime.timedelta(days=6),
        expires_at=utcnow() + datetime.timedelta(days=6)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    good_deal = StoreDeal(
        dataset_id=dataset.id,
        item_name="Amazing BOGO Weed",
        sale_price="$25.00",
        description="Buy 1 Get 1 Free"
    )
    filler_deal = StoreDeal(
        dataset_id=dataset.id,
        item_name="Overpriced Pre-Roll",
        sale_price="$15.00",
        description="Just a regular pre-roll"
    )
    db.add_all([good_deal, filler_deal])
    db.commit()
    db.close()

    client = TestClient(app)
    response = client.get("/dispensaries")
    assert response.status_code == 200
    html = response.text

    assert "Top Dispensary Deals" in html
    assert "Top 6 Dispensary Deals" not in html
    assert "Active Dispensary Menus" in html
    assert "Best Store This Week" in html

    # Verify score 1/10 filler items are excluded from top deals
    assert "Score: 1/10" not in html
    assert "Amazing BOGO Weed" in html
    assert "Overpriced Pre-Roll" not in html


@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_class", [
    PatriotCareScraper,
    RiseDispensaryScraper,
    LeafJoyScraper,
    HeirloomCollectionScraper,
    Pharmacy257Scraper,
    SmokeyLeafScraper,
    CheechAndChongScraper
])
async def test_dispensary_scrapers_fallback(scraper_class):
    """Verify dispensary scrapers return structured deals gracefully on timeout/error."""
    scraper = scraper_class()

    # Mock page.goto to raise an exception simulating timeout
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Simulated network timeout")

    result = await scraper.scrape(mock_page)

    # Assert expected structure
    assert isinstance(result, dict)
    assert result.get("kind") == "dispensary"
    assert result.get("scraper_key") == scraper.scraper_key
    assert "flyer_start_date" in result
    assert "flyer_end_date" in result

    # Verify deals
    deals = result.get("deals", [])
    assert len(deals) > 0
    assert result.get("items_scraped_count", 0) == len(deals)

    for deal in deals:
        assert isinstance(deal.get("price"), str)
        assert len(deal.get("price")) > 0
        assert isinstance(deal.get("name"), str)
        assert len(deal.get("name")) > 0
