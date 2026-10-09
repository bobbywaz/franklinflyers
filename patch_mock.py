import sys
from unittest.mock import MagicMock

def mock_get_active_grocery_datasets(db):
    from app.models import StoreDataset, StoreDeal
    from datetime import datetime, timedelta

    # Mock data to return
    dataset1 = StoreDataset(
        id=1,
        scraper_key="ALDI",
        store_name="ALDI",
        status="success",
        flyer_start_date=datetime.now().date(),
        flyer_end_date=datetime.now().date() + timedelta(days=7),
        deals=[
            StoreDeal(
                id=1,
                item_name="Mock Deal Grocery",
                description="Groceries",
                sale_price="$20.00"
            )
        ]
    )
    return [dataset1]

import app.store_utils
app.store_utils.get_active_grocery_datasets = mock_get_active_grocery_datasets

import app.main
app.main.get_active_grocery_datasets = mock_get_active_grocery_datasets
