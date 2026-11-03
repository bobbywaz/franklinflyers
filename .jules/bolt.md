## 2026-11-03 - N+1 Query on Admin Page
**Learning:** Found N+1 query loop when rendering admin cards calling `get_latest_attempt_by_key`, `_latest_success_by_key`, and `get_active_dataset_by_key` inside `for entry in manager.list_scrapers():` in `_build_admin_context`. This creates 3 queries per scraper which will scale poorly as scrapers increase.
**Action:** Use batched queries with `sqlalchemy.func.max(id).group_by(scraper_key)` and dictionary lookups instead of executing individual queries within the loop to fetch latest records.
