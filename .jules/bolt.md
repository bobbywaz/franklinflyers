
## 2024-05-18 - Fix N+1 queries on Admin Dashboard
**Learning:** Looping over DB entities like `manager.list_scrapers()` and calling functions like `get_latest_attempt_by_key` or `_latest_success_by_key` inside the loop causes significant N+1 queries problems in SQLAlchemy, reducing database performance dramatically.
**Action:** Use batched queries with `sqlalchemy.func.max(id).group_by()` in conjunction with dictionary lookup mappings to retrieve state for multiple records at once to achieve massive performance scaling improvements on dashboards, rather than individually querying per list element.
