import pytest
from app.database import Base, engine, SessionLocal, init_db

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    init_db()

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
