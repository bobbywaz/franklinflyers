import pytest
import datetime
from app.database import engine, SessionLocal
from app.models import Base, StoreDataset, Run, Deal, BestStore, StoreDeal

@pytest.fixture(autouse=True, scope="session")
def init_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Just create the tables, leave empty for now as some tests might rely on empty db logic
        # if they need seed data they should do it themselves or we can add minimal data here if strictly required
        pass
    finally:
        db.close()
    yield
