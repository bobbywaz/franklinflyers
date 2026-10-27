import pytest
from app.database import engine, Base
import app.models

@pytest.fixture(autouse=True, scope="session")
def initialize_database():
    Base.metadata.create_all(bind=engine)
    yield
