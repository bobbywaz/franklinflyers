from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine, SessionLocal
from app.models import StoreDataset, StoreDeal
import datetime

db = SessionLocal()
now = datetime.datetime.now()

# Add mock dispensary
dispensary = StoreDataset(
    scraper_key="patriot_care",
    store_name="Patriot Care",
    kind="dispensary",
    trigger_mode="manual",
    status="success",
    started_at=now,
    finished_at=now,
    flyer_start_date=now.date(),
    item_count=1
)
db.add(dispensary)
db.commit()

dispensary_deal = StoreDeal(
    dataset_id=dispensary.id,
    item_name="Mock Weed Deal",
    sale_price="10.00",
    description="Score: 10/10 - Excellent deal on premium flower."
)
db.add(dispensary_deal)
db.commit()

# Add mock grocery
grocery = StoreDataset(
    scraper_key="ALDI",
    store_name="ALDI",
    kind="grocery",
    trigger_mode="manual",
    status="success",
    started_at=now,
    finished_at=now,
    flyer_start_date=now.date(),
    item_count=1
)
db.add(grocery)
db.commit()

grocery_deal = StoreDeal(
    dataset_id=grocery.id,
    item_name="Mock Grocery Deal",
    sale_price="5.00"
)
db.add(grocery_deal)
db.commit()

# Add mock movie
movie = StoreDataset(
    scraper_key="greenfield_garden_cinemas",
    store_name="Greenfield Garden Cinemas",
    kind="movie",
    trigger_mode="manual",
    status="success",
    started_at=now,
    finished_at=now,
    flyer_start_date=now.date(),
    item_count=1
)
db.add(movie)
db.commit()

movie_deal = StoreDeal(
    dataset_id=movie.id,
    item_name="Mock Movie",
    description="Showtimes: " + now.strftime("%I:%M %p")
)
db.add(movie_deal)
db.commit()


# Add mock pharmacy
pharmacy = StoreDataset(
    scraper_key="cvs_greenfield",
    store_name="CVS",
    kind="pharmacy",
    trigger_mode="manual",
    status="success",
    started_at=now,
    finished_at=now,
    flyer_start_date=now.date(),
    item_count=1
)
db.add(pharmacy)
db.commit()

pharmacy_deal = StoreDeal(
    dataset_id=pharmacy.id,
    item_name="Mock Pharmacy Deal",
    sale_price="5.00"
)
db.add(pharmacy_deal)
db.commit()

db.close()
