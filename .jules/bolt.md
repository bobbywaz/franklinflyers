## 2024-11-09 - N+1 query problem in SQLAlchemy context builders
**Learning:** Found N+1 query bottlenecks in context builders like `_build_home_context` where lazy-loaded relationships (`deals`, `best_store`) on models like `Run` cause numerous hidden database queries during iteration or property access.
**Action:** Always proactively eager load scalar relationships using `joinedload(...)` and collection/nested relationships using `selectinload(...)` in the initial `db.query` to batch operations.
