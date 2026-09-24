## 2024-05-25 - N+1 Queries required options(joinedload(...)) instead of manual batching
**Learning:** Rendering complex context models (like the `Run` model) directly without preloading relationships like `deals` and `best_store` triggered massive N+1 query spam on the index and admin views.
**Action:** Use `.options(joinedload(Model.relationship))` explicitly on SQLAlchemy queries that fetch parent models destined for templates that iterate over their children.
