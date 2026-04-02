import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import Run, Deal, BestStore, FailedScrape
import datetime

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

from sqlalchemy.pool import StaticPool
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Setup test DB tables before each test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop test DB tables after each test
    Base.metadata.drop_all(bind=engine)


def test_read_root_no_data():
    """Test the root endpoint when there is no data in the database."""
    response = client.get("/")
    assert response.status_code == 200
    # Assuming 'has_data' would lead to rendering something like "No flyer data available yet." or not showing deals.
    assert b"Refresh Now" in response.content # Assuming Refresh Now button is always there


def test_read_root_with_data():
    """Test the root endpoint with a mock run and some deals."""
    db = TestingSessionLocal()

    # Insert mock data
    mock_run = Run(run_date=datetime.datetime.utcnow())
    db.add(mock_run)
    db.commit()
    db.refresh(mock_run)

    mock_best_store = BestStore(
        run_id=mock_run.id,
        store_name="Big Y",
        summary="Great produce.",
        strengths="Produce",
        weaknesses="Meat",
        score=8
    )
    db.add(mock_best_store)

    mock_failed_scrape = FailedScrape(
        run_id=mock_run.id,
        store_name="Stop & Shop",
        error_message="Timeout loading page."
    )
    db.add(mock_failed_scrape)

    mock_deal_1 = Deal(
        run_id=mock_run.id,
        store_name="Big Y",
        item_name="Apples",
        sale_price="$1.99/lb",
        description="Fresh local apples",
        category="Produce",
        score=9,
        explanation="Great value."
    )
    db.add(mock_deal_1)

    mock_deal_2 = Deal(
        run_id=mock_run.id,
        store_name="Big Y",
        item_name="Chicken Breast",
        sale_price="$2.99/lb",
        description="Boneless skinless",
        category="Meat",
        score=7,
        explanation="Average deal."
    )
    db.add(mock_deal_2)

    db.commit()
    db.close()

    response = client.get("/")
    assert response.status_code == 200

    content = response.content.decode()

    # Assert expected content is present in HTML
    assert "Big Y" in content
    assert "Apples" in content
    assert "Chicken Breast" in content
    assert "$1.99/lb" in content
    assert "Produce" in content
    assert "Meat" in content

    # Assert Best Store is shown
    assert "Great produce." in content

    # Assert failed scrape is shown
    assert "Stop &amp; Shop" in content or "Stop & Shop" in content
    assert "Timeout loading page." in content
