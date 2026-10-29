## 2024-05-15 - [Database N+1 Issue in Context Builders]
**Learning:** Found N+1 query problems in database calls inside `_build_home_context` where `Run` relations are not eager-loaded.
**Action:** Always eager-load related data (e.g. `deals`, `best_store`) when querying the database for `Run` instances.
