import pytest
from app.database import Base, SessionLocal, engine, init_db
from app.models import StoreDataset, StoreDeal, Run, Deal, Configuration
import datetime
import zoneinfo
import json
import os

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    db = SessionLocal()

    existing = db.query(StoreDataset).filter(StoreDataset.scraper_key == "walgreens_greenfield").first()
    if existing:
        db.close()
        return

    tz = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.datetime.now(tz)

    grocery_ds = StoreDataset(
        scraper_key="aldi",
        store_name="ALDI",
        kind="grocery",
        trigger_mode="test",
        status="success",
        flyer_start_date=now.date() - datetime.timedelta(days=1),
        flyer_end_date=now.date() + datetime.timedelta(days=6),
        expires_at=now + datetime.timedelta(days=6),
        items_scraped_count=1,
        item_count=1
    )
    db.add(grocery_ds)
    db.commit()

    run = Run(
        run_date=now,
        is_ready=True,
        seasonal_info=None,
        recipe_idea=None
    )
    db.add(run)
    db.commit()

    deal = Deal(
        run_id=run.id,
        store_name="ALDI",
        category="Produce",
        item_name="Apples",
        description="Fresh apples",
        sale_price="$1.99",
        score=9,
        explanation="Great price"
    )
    db.add(deal)
    db.commit()

    dispensary_ds = StoreDataset(
        scraper_key="patriot_care",
        store_name="Patriot Care",
        kind="dispensary",
        trigger_mode="test",
        status="success",
        flyer_start_date=now.date() - datetime.timedelta(days=1),
        flyer_end_date=now.date() + datetime.timedelta(days=6),
        expires_at=now + datetime.timedelta(days=6),
        items_scraped_count=10,
        item_count=10
    )
    db.add(dispensary_ds)
    db.commit()

    deal1 = StoreDeal(
        dataset_id=dispensary_ds.id,
        item_name="Super Silver Haze 3.5g",
        sale_price="$25.00",
        description="Sale from $50.00"
    )
    db.add(deal1)

    movie_ds = StoreDataset(
        scraper_key="greenfield_garden_cinemas",
        store_name="Garden Cinemas",
        kind="movie",
        trigger_mode="test",
        status="success",
        flyer_start_date=now.date() - datetime.timedelta(days=1),
        flyer_end_date=now.date() + datetime.timedelta(days=6),
        expires_at=now + datetime.timedelta(days=6),
        items_scraped_count=1,
        item_count=1
    )
    db.add(movie_ds)
    db.commit()

    t1 = now.replace(hour=16, minute=15) + datetime.timedelta(hours=1)
    t1_str = t1.strftime("%I:%M %p").lstrip('0')
    deal2 = StoreDeal(
        dataset_id=movie_ds.id,
        item_name="The Matrix",
        sale_price=t1_str,
        description="PG-13 | 120 min | Tickets: http://example.com/tickets"
    )
    db.add(deal2)

    pharmacy_ds = StoreDataset(
        scraper_key="walgreens_greenfield",
        store_name="Walgreens",
        kind="pharmacy",
        trigger_mode="test",
        status="success",
        flyer_start_date=now.date() - datetime.timedelta(days=1),
        flyer_end_date=now.date() + datetime.timedelta(days=6),
        expires_at=now + datetime.timedelta(days=6),
        items_scraped_count=1,
        item_count=1
    )
    db.add(pharmacy_ds)
    db.commit()

    deal3 = StoreDeal(
        dataset_id=pharmacy_ds.id,
        item_name="Advil",
        sale_price="$5.00",
        description="Buy 1 Get 1 Free | ExtraBucks Rewards"
    )
    db.add(deal3)
    db.commit()

    from app.gemini_analyzer import GeminiAnalyzer
    import asyncio
    async def create_analysis():
        return await GeminiAnalyzer().analyze_pharmacy_deals([
            {
                "id": deal3.id,
                "store_name": pharmacy_ds.store_name,
                "scraper_key": pharmacy_ds.scraper_key,
                "town": "Greenfield",
                "name": deal3.item_name,
                "price": deal3.sale_price,
                "description": deal3.description,
                "image_url": "",
                "store_info": {},
                "flyer_start": str(pharmacy_ds.flyer_start_date),
                "flyer_end": str(pharmacy_ds.flyer_end_date),
            }
        ])
    analysis = asyncio.run(create_analysis())

    sig = f"{pharmacy_ds.id}_{pharmacy_ds.finished_at.isoformat() if pharmacy_ds.finished_at else ''}_{len(pharmacy_ds.deals)}"

    existing_conf = db.query(Configuration).filter_by(key="pharmacy_ai_analysis").first()
    if existing_conf:
        db.delete(existing_conf)
        db.commit()

    c = Configuration(key="pharmacy_ai_analysis", value=json.dumps({"sig": sig, "analysis": analysis}))
    db.add(c)
    db.commit()

    db.close()
