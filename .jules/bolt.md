
## 2024-05-16 - Prevent N+1 queries when accessing relationships on Run model
**Learning:** Querying the `Run` model and subsequently accessing its relationships (like `best_store`, `deals`, or `published_stores.dataset`) without eager loading within the context builders causes severe N+1 lazy loading performance regressions because it executes an individual query for every relationship lookup.
**Action:** When querying the `Run` model, explicitly eager load needed relationships using SQLAlchemy's `joinedload` (for scalar relationships like `best_store`) and `selectinload` (for collection relationships like `deals` and `published_stores`).
