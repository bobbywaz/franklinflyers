## 2023-10-27 - [N+1 Queries on `dataset.deals`]
**Learning:** `get_active_*_datasets` functions in `app/store_utils.py` fetch lists of `StoreDataset` objects which are iterated over in `app/main.py`. The `.deals` relationship was not eagerly loaded, causing an N+1 query problem where accessing `.deals` resulted in a separate database query per dataset.
**Action:** Use `selectinload(StoreDataset.deals)` in `get_active_*_datasets` methods when querying from the database to eagerly load related `deals` in a single query and prevent N+1 issues.
