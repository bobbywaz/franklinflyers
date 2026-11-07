## 2024-03-24 - N+1 Queries in FastAPI Context Builders
**Learning:** Accessing lazy-loaded SQLAlchemy relationships (like `Run.deals`) inside synchronous FastAPI view builders (like `_build_home_context`) causes implicit N+1 database queries that block the main thread and degrade performance.
**Action:** Always explicitly eager load required scalar relationships using `joinedload` and collection relationships using `selectinload` when fetching the base model.
