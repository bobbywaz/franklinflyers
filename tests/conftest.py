import pytest
from app.database import engine
from app.models import Base

@pytest.fixture(autouse=True, scope="session")
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield
