## 2024-10-28 - [Eager Load Relationships for Context Builders]
**Learning:** Context builders like `_build_home_context` and `_build_admin_context` frequently access related `Run` objects (`best_store`, `deals`, `published_stores`) causing N+1 database queries due to lazy loading.
**Action:** Use `.options(joinedload(...))` for scalar relationships and `.options(selectinload(...))` for collections to prefetch relationships during the initial query in `_build_home_context` and `_build_admin_context`.
