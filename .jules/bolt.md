
## 2024-05-18 - Prevent N+1 queries in context builders
**Learning:** In SQLAlchemy, accessing lazy-loaded relationships inside a loop or during response serialization causes N+1 queries, severely impacting backend performance. In our `app/main.py` context builders, retrieving the `latest_run` without eager loading triggers extra queries when accessing `Run.deals`, `Run.best_store`, and `Run.published_stores.dataset`.
**Action:** Always use SQLAlchemy's eager loading options like `joinedload` (for scalar relationships) and `selectinload` (for collections) on queries that fetch objects whose relationships will be heavily accessed in the response loop or context builder.
