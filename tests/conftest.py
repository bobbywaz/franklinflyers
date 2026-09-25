import pytest
from app.database import Base, engine, SessionLocal
from seed_test_db import seed_for_tests

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_for_tests(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
