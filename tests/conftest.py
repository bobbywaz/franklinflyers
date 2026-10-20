import pytest
from app.database import engine, Base
import app.main

@pytest.fixture(autouse=True, scope="session")
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.main.init_db()
    yield
