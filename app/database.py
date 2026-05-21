from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./franklin_flyers.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_runtime_columns()


def _ensure_runtime_columns():
    inspector = inspect(engine)
    if "store_datasets" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("store_datasets")}
    if "items_scraped_count" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE store_datasets ADD COLUMN items_scraped_count INTEGER DEFAULT 0")
            )
            connection.execute(
                text(
                    "UPDATE store_datasets SET items_scraped_count = COALESCE(item_count, 0)"
                )
            )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
