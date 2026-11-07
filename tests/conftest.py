import pytest
from app.database import Base, engine
import app.models  # Required so Base knows about all tables

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
