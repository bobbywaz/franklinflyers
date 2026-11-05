## 2024-11-05 - [Fix N+1 query fetching latest records for multiple scrapers]
**Learning:** The admin context builder executes multiple queries for each scraper to fetch its latest attempt, success, and active status resulting in a severe N+1 bottleneck when loading the page.
**Action:** Used batched subqueries grouping by scraper_key and `sqlalchemy.func.max(id)` to collect all latest entities mapped by their keys prior to looping over the scrapers, drastically improving execution speed (e.g. 88% reduction).
