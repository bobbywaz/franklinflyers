
## 2024-05-18 - SQLAlchemy N+1 Query Optimization
**Learning:** In the `_build_admin_context` and `_build_home_context` builders, querying the `latest_run` without eager loading triggers significant N+1 queries when accessing related deals, datasets, and published stores properties, resulting in around 80+ queries for a single request.
**Action:** When querying models like `Run` that load collections (e.g., deals) and scalar relationships (e.g., best_store) to be used immediately in templates or functions, explicitly use `.options(selectinload(...), joinedload(...))` to eagerly fetch them. `joinedload` prevents N+1 for scalars, while `selectinload` avoids Cartesian product explosions for collections.
