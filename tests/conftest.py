import pytest
from app.database import Base, engine

@pytest.fixture(scope="session", autouse=True)
def setup_db_session():
    Base.metadata.create_all(bind=engine)
    yield
