## 2024-10-24 - N+1 query in admin context
**Learning:** `_build_admin_context` does O(N) queries when loading `StoreDataset` records for scrapers. Batched queries avoid this.
**Action:** Use `func.max().group_by()` and dict lookups to batch fetch latest entries.
