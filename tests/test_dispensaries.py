import pytest
from starlette.testclient import TestClient

from app.database import Base, SessionLocal, engine
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
    import datetime
    from app.database import get_db

    db = next(app.dependency_overrides.get(get_db, get_db)()) if hasattr(app, "dependency_overrides") and get_db in app.dependency_overrides else SessionLocal()
    # clean db first
    db.query(StoreDataset).delete()

    # insert mock data
    dataset = StoreDataset(
        store_name="Mock Dispensary",
        scraper_key="mock_dispensary",
        kind="dispensary",
        trigger_mode="manual",
        flyer_start_date=datetime.date.today(),
        flyer_end_date=datetime.date.today() + datetime.timedelta(days=7),
        status="success",
        expires_at=utcnow() + datetime.timedelta(days=7)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    deal1 = StoreDeal(dataset_id=dataset.id, item_name="Good Weed", sale_price="$25.00", description="BOGO Free")
    deal2 = StoreDeal(dataset_id=dataset.id, item_name="Bad Weed", sale_price="$50.00", description="Regular price")
    db.add_all([deal1, deal2])
    db.commit()

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

    db.query(StoreDataset).delete()
    db.commit()
    db.close()
