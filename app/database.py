from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./franklin_flyers.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30}
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

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
