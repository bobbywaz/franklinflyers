import re
from starlette.testclient import TestClient
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    from app.database import Base, engine, SessionLocal
    from app.models import StoreDataset, StoreDeal, Run, Deal, BestStore, PublishedSnapshotStore, Configuration
    import datetime
    from app.store_utils import utcnow

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Needs a latest run
    run = Run(is_ready=True)
    run.best_store = BestStore(store_name="ALDI", score=10)

    dataset = StoreDataset(scraper_key="aldi", store_name="ALDI", kind="grocery", status="success", trigger_mode="manual", expires_at=utcnow()+datetime.timedelta(days=1))
    db.add(dataset)
    db.commit()

    pub_store = PublishedSnapshotStore(scraper_key="aldi", store_name="ALDI", dataset=dataset)
    run.published_stores = [pub_store]

    deal = Deal(store_name="ALDI", item_name="Test Item", category="produce", score=10)
    run.deals = [deal]
    db.add(run)
    db.commit()

    yield
    db.close()

from app.main import app


def test_home_store_filter_checkboxes():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text

    # Store filters container and checkboxes
    assert 'id="store-filters"' in html
    assert 'class="store-checkbox' in html
    assert 'data-store-checkbox=' in html
    assert 'store-filter-pill' in html

    # Deals markup
    assert 'deal-card' in html
    assert 'data-store=' in html
    assert 'deal-item' in html
    assert 'data-category-block' in html

    # Empty state placeholders
    assert 'id="top-overall-empty"' in html
    assert 'id="deals-by-category-empty"' in html

    # Filter script presence and persistence
    assert "ff_grocery_store_filter" in html
    assert "applyFilter" in html
    assert "localStorage" in html
