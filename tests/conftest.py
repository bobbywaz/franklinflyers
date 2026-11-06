import pytest
from app.database import Base, engine, init_db

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    yield
