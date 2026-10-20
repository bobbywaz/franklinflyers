## 2024-05-24 - N+1 in Run model

## 2024-05-24 - N+1 database querying on dashboard views
**Learning:** Found a major N+1 query problem in `app/main.py`'s `_build_admin_context` where it iterated over 25+ scrapers, executing 3 queries each to fetch the latest attempt, latest success, and active datasets. This caused over 100 queries to execute just to load the admin dashboard.
**Action:** Used `func.max(id).group_by(scraper_key)` subqueries joined back to the main table to batch fetch all latest records in only 3 total queries. Pre-fetched the results into dictionaries keyed by `scraper_key` so the loop could rely on O(1) dictionary lookups `.get()` instead of O(N) database queries. Apply this batching pattern to all future list/dashboard endpoints handling multiple entity instances.
