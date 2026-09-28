import re

def patch_file():
    with open('app/main.py', 'r') as f:
        content = f.read()

    new_code = """
    cards = []
    latest_published_datasets = [entry.dataset for entry in latest_run.published_stores if entry.dataset] if latest_run else []

    scraper_keys = [entry["scraper_key"] for entry in manager.list_scrapers() if entry["scraper_key"] not in ("full_run", "grocery_run")]
    from sqlalchemy import func
    from .store_utils import utcnow, STATUS_SUCCESS

    # Batch load latest attempts
    latest_attempt_sq = db.query(
        StoreDataset.scraper_key,
        func.max(StoreDataset.finished_at).label('max_finished_at')
    ).filter(StoreDataset.scraper_key.in_(scraper_keys)).group_by(StoreDataset.scraper_key).subquery()

    latest_attempts = db.query(StoreDataset).join(
        latest_attempt_sq,
        (StoreDataset.scraper_key == latest_attempt_sq.c.scraper_key) &
        (StoreDataset.finished_at == latest_attempt_sq.c.max_finished_at)
    ).all()
    latest_attempts_by_key = {d.scraper_key: d for d in latest_attempts}

    # Batch load latest successes
    latest_success_sq = db.query(
        StoreDataset.scraper_key,
        func.max(StoreDataset.finished_at).label('max_finished_at')
    ).filter(
        StoreDataset.scraper_key.in_(scraper_keys),
        StoreDataset.status == STATUS_SUCCESS
    ).group_by(StoreDataset.scraper_key).subquery()

    latest_successes = db.query(StoreDataset).join(
        latest_success_sq,
        (StoreDataset.scraper_key == latest_success_sq.c.scraper_key) &
        (StoreDataset.finished_at == latest_success_sq.c.max_finished_at)
    ).all()
    latest_successes_by_key = {d.scraper_key: d for d in latest_successes}

    # Batch load active datasets
    now = utcnow()
    active_dataset_sq = db.query(
        StoreDataset.scraper_key,
        func.max(StoreDataset.finished_at).label('max_finished_at')
    ).filter(
        StoreDataset.scraper_key.in_(scraper_keys),
        StoreDataset.status == STATUS_SUCCESS,
        StoreDataset.expires_at != None,
        StoreDataset.expires_at >= now
    ).group_by(StoreDataset.scraper_key).subquery()

    active_datasets = db.query(StoreDataset).join(
        active_dataset_sq,
        (StoreDataset.scraper_key == active_dataset_sq.c.scraper_key) &
        (StoreDataset.finished_at == active_dataset_sq.c.max_finished_at)
    ).all()
    active_datasets_by_key = {d.scraper_key: d for d in active_datasets}

    for entry in manager.list_scrapers():
        scraper_key = entry["scraper_key"]
"""

    content = re.sub(
        r'\s*cards = \[\]\n\s*latest_published_datasets = \[entry\.dataset for entry in latest_run\.published_stores if entry\.dataset\] if latest_run else \[\]\n\n\s*for entry in manager\.list_scrapers\(\):\n\s*scraper_key = entry\["scraper_key"\]\n',
        new_code,
        content
    )

    content = re.sub(
        r'latest_attempt = get_latest_attempt_by_key\(db, scraper_key\)',
        r'latest_attempt = latest_attempts_by_key.get(scraper_key)',
        content
    )
    content = re.sub(
        r'latest_success = _latest_success_by_key\(db, scraper_key\)',
        r'latest_success = latest_successes_by_key.get(scraper_key)',
        content
    )
    content = re.sub(
        r'active_dataset = get_active_dataset_by_key\(db, scraper_key\)',
        r'active_dataset = active_datasets_by_key.get(scraper_key)',
        content
    )

    with open('app/main.py', 'w') as f:
        f.write(content)

patch_file()
