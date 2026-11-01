## 2024-11-01 - N+1 query in Admin Context
**Learning:** `_build_admin_context` loops over all scrapers (~30) and performs multiple queries inside the loop (`get_latest_attempt_by_key`, `_latest_success_by_key`, `get_active_dataset_by_key`), leading to ~90 database queries per page load.
**Action:** Replace the individual queries inside the loop with batched queries for `latest_attempt`, `latest_success`, and `active_dataset` using `func.max(id)` or `func.max(finished_at)` group by `scraper_key`.
