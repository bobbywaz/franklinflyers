import re

def patch_file():
    with open('app/main.py', 'r') as f:
        content = f.read()

    # Step 1: Fix imports for selectinload and joinedload
    content = re.sub(
        r'from sqlalchemy.orm import Session\n',
        r'from sqlalchemy.orm import Session, joinedload, selectinload\n',
        content
    )

    # Step 2: Add PublishedSnapshotStore to models import
    content = re.sub(
        r'from \.models import Configuration, Run, StoreDataset\n',
        r'from .models import Configuration, Run, StoreDataset, PublishedSnapshotStore\n',
        content
    )

    # Step 3: Optimize _build_home_context
    content = re.sub(
        r'def _build_home_context\(request: Request, db: Session\):\n    latest_run = db.query\(Run\).filter\(Run.is_ready == True\).order_by\(Run.run_date.desc\(\)\).first\(\)\n',
        r'def _build_home_context(request: Request, db: Session):\n    latest_run = db.query(Run).options(joinedload(Run.best_store), selectinload(Run.deals)).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()\n',
        content
    )

    # Step 4: Optimize _build_admin_context
    content = re.sub(
        r'def _build_admin_context\(request: Request, db: Session, message: str = None, error: str = None\):\n    manager = ScraperManager\(\)\n    latest_run = db.query\(Run\).filter\(Run.is_ready == True\).order_by\(Run.run_date.desc\(\)\).first\(\)\n',
        r'def _build_admin_context(request: Request, db: Session, message: str = None, error: str = None):\n    manager = ScraperManager()\n    latest_run = db.query(Run).options(selectinload(Run.published_stores).joinedload(PublishedSnapshotStore.dataset), selectinload(Run.deals)).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()\n',
        content
    )

    # Write back
    with open('app/main.py', 'w') as f:
        f.write(content)

patch_file()
