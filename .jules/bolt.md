## 2024-11-20 - N+1 Query Problem in Store Utils
**Learning:** `get_active_*_datasets` functions in `app/store_utils.py` currently fetch datasets but don't eager load the `deals` relationship. Because many routes (like `/dispensaries`, `/events`, `/movies`, and `/pharmacies`) iterate through these datasets and access `dataset.deals`, this causes an N+1 query problem, making a separate database query to fetch deals for each active dataset.
**Action:** Use SQLAlchemy's `selectinload` (or `joinedload`) to eagerly load relationships in these shared utility queries to prevent N+1 bottlenecks.
