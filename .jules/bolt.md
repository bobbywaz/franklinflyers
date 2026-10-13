## 2024-05-24 - Fix N+1 queries in admin and home contexts
**Learning:** Using `joinedload` on collection relationships (e.g., `Run.deals`) can cause Cartesian product memory explosions, but lazy loading them causes severe N+1 queries (e.g. iterating over scraper lists and accessing `dataset.items_scraped_count`).
**Action:** Use `selectinload` for collection relationships (e.g., `deals`, `published_stores`) and `joinedload` for scalar relationships (e.g., `best_store` or nested `PublishedSnapshotStore.dataset`) within `.options()` when querying models that are accessed frequently in loops.
