# Franklin Flyers Agent Guide

Read this before changing the project. Keep this file updated when architecture, scraper behavior, or operational commands change.

## Project

- Stack: FastAPI, Jinja, SQLite/SQLAlchemy, Playwright, Gemini.
- Runtime: Docker Compose.
- App entrypoint: `app/main.py`.
- Web port: host `8001` to container `8000`.
- Database: `franklin_flyers.db`.
- Public pages: `/`, `/dispensaries`, `/events`, `/movies`, `/pharmacies`.
- Admin: `/admin`, protected by session authentication.

## Architecture

- `app/manager.py` owns the scraper registry and Playwright execution.
- `app/scheduler.py` runs scrapers, persists attempts, publishes grocery snapshots, and manages refresh jobs.
- `app/store_utils.py` owns date parsing, active-dataset queries, expiry windows, and result normalization.
- `app/models.py` contains legacy published-snapshot models plus current store-level models.
- `app/scrapers/` contains one scraper per source.
- `templates/` contains the public and admin UI.
- `tests/` contains permanent automated tests.

Store-level persistence is the source of truth:

- `store_datasets`: one record per scraper attempt and its validity window.
- `store_deals`: normalized items/events belonging to a dataset.
- A failed attempt must not erase an older still-valid successful dataset.
- `runs`, `deals`, `best_stores`, and `published_snapshot_stores` are published grocery-analysis snapshots, not raw scraper history.

## Strict Zero-Mock Policy

Under NO circumstances should mock listings, dummy test data, synthetic placeholders, or the word "mock" ever be rendered to users or persisted into production database tables (`deals`, `best_stores`, `store_deals`, `runs`, `configurations`).

1. **No Fake / Mock Text**:
   - Never write phrases like `"This is a mock evaluation for..."` or `"...in our mock analysis."` into deal explanations, store summaries, recipe ideas, or UI templates.
   - All public listings must represent authentic, scraped circular data or real local community events.

2. **Resilient Rule-Based Fallbacks**:
   - External AI services (such as the Gemini API) can be unavailable, time out, or run out of credits (e.g. HTTP 402 `RESOURCE_EXHAUSTED`).
   - When Gemini or external AI fails or is unconfigured, fallback handling MUST be strictly deterministic and rule-based (e.g. `_score_grocery_item`, `_rule_based_analyze`, `_score_pharmacy_item`, `_rule_based_analyze_pharmacy`) or use genuine curated circular items.
   - Rule-based analysis must calculate realistic scores (1-10) based on actual pricing signals (BOGO, volume free, price/lb, bundle discounts) and generate factual, professional explanations and store evaluations.
   - Seasonal guides and recipe generators must derive from actual calendar seasons and authentic deal ingredients, never hardcoded dummy strings.

3. **Test Isolation**:
   - Mocks, MagicMocks, and synthetic test fixtures are strictly restricted to the `tests/` directory.
   - Test-only mocks must never leak into application code (`app/`), scraper execution, fallback logic, or database storage.

## Deal Curation Policy (Zero-Filler, No Hard Cap)

The entire purpose of Franklin Flyers is to highlight only genuine, high-value deals and protect users from supermarket promotional filler ("if it's a really good deal show it, otherwise don't"):

1. **No Artificial Hard Number Cap**:
   - Do not enforce an artificial hard number or quota (e.g. capped at 20 groceries, 6 dispensaries, or 8 pharmacies).
   - If there are 18 standout deals across our local stores this week, show 18. If there are 45, show all 45.

2. **Qualifying Standout Grocery Deals (Score $\ge$ 8 Only)**:
   - Only genuinely great deals qualify for publication:
     * **BOGO Free & Volume Free Deals**: True Buy 1 Get 1 Free, Buy 2 Get 2 Free, straight 50% discounts (scores 9–10).
     * **Stock-Up $1 Mix & Match**: 10 for $10, 5 for $5, 4 for $4, or essential staples priced $\le$ $1.50.
     * **Deep Protein Discounts**: Poultry $\le$ $1.49/lb (e.g. 99¢ drumsticks/quarters), boneless chicken breast/tenders $\le$ $2.49/lb, fresh pork $\le$ $3.49/lb, ground beef $\le$ $4.99/lb, beef roasts/steaks $\le$ $6.99/lb, fresh salmon/shrimp $\le$ $9.99/lb.
     * **True Produce Bargains**: Fruits and vegetables $\le$ $1.00/lb (e.g. 88¢/99¢ apples, 99¢ peppers/squash, 49¢ bananas) or bulk produce bags $\le$ $2.99.

3. **Qualifying Standout Weed / Dispensary Deals (Score $\ge$ 8 Only)**:
   - True BOGO / 50%+ off: Score 10.
   - 30% - 49% off: Score 9 (e.g. $40 flower down to $28, $45 vape down to $30).
   - 20% - 29% off: Score 8 (verified promotional sale).
   - Regular menu items and discounts < 10% (scores 1–5) are excluded as filler.

4. **Qualifying Standout Pharmacy Deals (Score $\ge$ 8 Only)**:
   - True BOGOs, Buy 1 Get 2 Free, Buy 2 Get 2 Free: Scores 9–10.
   - High-value rewards ($10+ ExtraBucks / Walgreens cash): Scores 9–10.
   - Standard 20¢ manufacturer coupons and baseline retail pricing (scores $\le$ 6) are excluded as filler.

5. **Zero-Cost Rule Engine & Legacy Gemini API Archive**:
   - All AI analysis and curation across groceries, dispensaries, and pharmacies run deterministically at $0 API cost using the user's host Antigravity (`agy`) subscription.
   - All legacy Google GenAI API client calls, prompts, and JSON parsers are preserved safely in `app/legacy_gemini.py`.
   - By default, `USE_LEGACY_GEMINI=false`, preventing paid Gemini API token usage or 402 `RESOURCE_EXHAUSTED` billing errors. Set `USE_LEGACY_GEMINI=true` only if Gemini API credits are funded.

## Scraper Registry

Current registered keys, in manager order by category:

- Grocery: `aldi`, `big_y`, `food_city`, `stop_and_shop`, `fosters`
- Dispensary: `patriot_care`, `rise_dispensary`, `leaf_joy`, `heirloom_collection`, `pharmacy_257`, `smokey_leaf`, `cheech_and_chong`
- Pharmacy: `cvs_greenfield`, `walgreens_greenfield`, `walgreens_turners_falls`
- Events: `shea_theater`, `rendezvous`, `tree_house`, `northampton_live`, `four_phantoms`, `franklin_chamber`, `shelburne_falls`, `visit_greenfield`
- Movies: `greenfield_garden_cinemas`, `cinemark_hadley`

`grocery_run` and `full_run` are synthetic admin cards, not scraper keys. Hawks & Reed is retired and must not be re-added; stale `hawks_and_reed` event datasets are excluded from active event results.

Every scraper should return a normalized result through `BaseScraper.build_result()`:

- Grocery: `kind="grocery"`, `deals`, `items_scraped_count`, flyer dates, expiry, next refresh.
- Dispensary: `kind="dispensary"`, `deals`, `items_scraped_count`, dates, expiry, next refresh.
- Pharmacy: `kind="pharmacy"`, `deals`, `items_scraped_count`, flyer dates, expiry, next refresh.
- Events: `kind="event"`, `deals`, and event date/time in the deal data whenever the source provides it.
- Movies: `kind="movie"`, `deals`, `items_scraped_count`, show dates, expiry, next refresh.
- A failed or empty result is persisted as a failed attempt by the scheduler.


## Event Rules

Anything added to `/events` must display the source data on this site:

- Scrape and render available date/time, location, and description.
- A `View details` link may supplement the rendered content, but link-only listings are not acceptable.
- Prefer direct HTML, JSON-LD, RSS, iCal, or API extraction.
- Do not use Gemini for ordinary event details.
- Store source detail URLs in descriptions or structured fields so the UI can render a clean link.
- Dated events are filtered out after their event date; undated recurring fallback entries remain until their dataset refreshes.
- Today's activity wheel incorporates upcoming movie showtimes strictly within the next few hours (2.5 hours, deduplicated across theaters, capped at 8 nearest showtimes) interleaved with today's community events.
- Keep each source link in `read_events()` and its venue badge/card in `templates/events.html`.

Current event sources:

- Shea Theater extracts upcoming shows from `https://sheatheater.org/calendar` with resilient event fallbacks.
- The Rendezvous uses structured recurring weekly community event fallbacks pointing to `https://thevoo.net/events/`.
- Tree House extracts Deerfield campus events from `https://treehousebrew.com/live-music-and-events` with resilient fallback.
- Northampton Live reads `#calendar .event.upcoming a` and fetches detail pages for time, location, and description.
- Four Phantoms uses structured recurring taproom event fallbacks pointing to `https://fourphantoms.com/lander`.
- Franklin County Chamber reads the monthly calendar at `https://chamber.franklincc.org/events/calendar/` with fallback to rolling event cards. This source also includes the Greenfield Farmers Market and other regional listings.
- Shelburne Falls paginates event cards and dates from `https://www.shelburnefalls.com/calendar/` across multiple pages without Gemini.
- Visit Greenfield extracts municipal, community, arts, and library events from `https://visitgreenfieldma.com/events/` via The Events Calendar REST API with Playwright DOM and curated local fallbacks.

## Grocery Scraper Notes

- ALDI: the old Flipp URL redirects to the current storefront. Extract storefront product cards directly; retain the legacy iframe path only as fallback. Gemini is used for the screenshot-analysis fallback.
- Big Y: uses FlareSolverr cookies/UA, in-browser store API activation, and Flipp `button.item-overlay` labels. Use `wait_until="commit"` for the weekly-ad page. ZIP search is `01376`; Greenfield may resolve to store ZIP `01301`.
- Food City: downloads the weekly-ad PDF and uses Gemini extraction. If Gemini credits are depleted or unavailable, it uses PDF URL date extraction and resilient weekly circular deal fallbacks for Turners Falls.
- Foster's: downloads its weekly-ad PDF and extracts deals and dates directly from the InDesign vector PDF text streams with pure local parsing, with Gemini extraction as optional secondary fallback.
- Stop & Shop: use the Backflipp API path first for Greenfield (`postal_code=01376`, store code `0442`); browser extraction is only fallback because of anti-bot challenges.

## Movie Scraper Notes

- Greenfield Garden Cinemas: uses direct `httpx` GET of `https://www.gardencinemas.net/` with Playwright fallback; parses movies, showtimes, ratings, runtime, poster images, trailer links, and online ticketing URLs.
- Cinemark Hampshire Mall (Hadley): scrapes `https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd` using Playwright with `wait_until="domcontentloaded"` and `wait_for_selector(".showtimeMovieBlock")`. Extracts formats (XD, RealD 3D), showtimes, seatmap ticket URLs, ratings, and posters. Do not use `wait_until="networkidle"` due to long-lived telemetry connections.

## Pharmacy Scraper Notes

- CVS Pharmacy (Greenfield): queries the Backflipp circular items API (`postal_code=01301`, `q="CVS"`) for store #1094 at 137 Federal St. Extracts weekly promotions, ExtraBucks rewards, categories, product images, and circular dates, with resilient curated fallback deals. Note: Turners Falls residents use this location across the river as there is no physical CVS in Turners Falls/Montague.
- Walgreens (Greenfield): queries the Backflipp circular items API (`postal_code=01301`, `q="Walgreens"`) for store #10672 at 5 Pierce St. Extracts weekly promotions, myWalgreens digital coupon discounts, categories, product images, and circular dates.
- Walgreens (Turners Falls): queries the Backflipp circular items API (`postal_code=01376`, `q="Walgreens"`) for store #17960 at 240 Avenue A in Turners Falls. Extracts town-specific circular deals, categories, product images, and circular dates.
- Pharmacy Deal Analysis: `GeminiAnalyzer.analyze_pharmacy_deals` categorizes all circular items into 6 standardized departments (`Vitamins & Supplements`, `Health & Medicine`, `Personal Care & Beauty`, `Household & Paper Goods`, `Snacks & Beverages`, `Baby & Family`), assigns 1–10 value scores and rationale explanations, picks a weekly pharmacy winner, and caches results in `configurations` table (`key="pharmacy_ai_analysis"`).


## Scheduling

- Do not add a fixed weekday full-scrape cron for normal refreshes.
- Each successful dataset gets `expires_at` and `next_refresh_at`, normally one day before its flyer/event window ends.
- APScheduler installs one date-triggered refresh job per scraper from `next_refresh_at`.
- Overdue scheduled refresh jobs are staggered in 20-second increments to avoid APScheduler burst collisions.
- **Scraper Concurrency & Serialization**: Scraper executions (single runs, grocery batch runs, and full runs) are strictly serialized through an asyncio concurrency lock (`_scrape_lock` in `app/scheduler.py`). Multiple simultaneous trigger requests (manual or scheduled) are queued and executed one-at-a-time to prevent Playwright resource exhaustion, FlareSolverr session conflicts, and SQLite database locking. Duplicate manual triggers for an already queued/running scraper are safely deduplicated.
- **Browser Context Isolation**: Batch executions (`run_grocery_batch`, `run_full_batch`) allocate and close an isolated browser context (`browser.new_context()`) per scraper to prevent cookie/session collisions and memory leaks.
- **Automated Antigravity (`agy`) Cron Curation**: A recurring cron job on the host system (`/mnt/docker/franklinflyers/scripts/cron_agy_curate.sh`) runs twice daily (07:30 & 19:30 EDT / 11:30 & 23:30 UTC: `30 11,23 * * *`). It launches `agy -p` non-interactively using the host Antigravity subscription ($0 Gemini token/API cost), checks active store datasets, triggers any needed single-store refreshes, and publishes an updated snapshot enforcing the Top 20 Zero-Filler deal policy. Logs are written to `/mnt/docker/franklinflyers/logs/agy_curate.log`.
- Manual full runs remain available and republish the combined grocery snapshot.
- Manual grocery runs (`run_grocery_scrape`) run all grocery scrapers sequentially and republish the snapshot.
- Manual single runs update only that scraper and can repair a missing public dataset.
- A dataset whose refresh time has passed gets a short retry fallback rather than a stale permanent schedule.

## Admin and Security

- Admin authentication uses Starlette `SessionMiddleware`.
- The admin password is stored in `configurations` under `admin_password`.
- Gemini credentials come from `GEMINI_API_KEY` in the root `.env`; never print or commit the value.
- Do not restore the old per-action password or `/api/refresh?pin=...` workflow without a deliberate design change.

## Commands

Start or rebuild the app:

```bash
cd /mnt/docker/franklinflyers
docker compose up -d --build
```

Watch the web service:

```bash
docker compose logs -f web
```

Run one scraper:

```bash
docker compose exec -T web python - <<'PY'
import asyncio
from app.scheduler import run_single_scrape
asyncio.run(run_single_scrape("big_y", trigger_mode="manual_single"))
PY
```

Run a grocery-only batch:

```bash
docker compose exec -T web python - <<'PY'
import asyncio
from app.scheduler import run_grocery_scrape
asyncio.run(run_grocery_scrape(trigger_mode="manual_grocery"))
PY
```

Run a full scrape:

```bash
docker compose exec -T web python - <<'PY'
import asyncio
from app.scheduler import run_full_scrape
asyncio.run(run_full_scrape(trigger_mode="manual_full"))
PY
```

Run host Antigravity automated curation:

```bash
/mnt/docker/franklinflyers/scripts/cron_agy_curate.sh
# Tail logs:
tail -f /mnt/docker/franklinflyers/logs/agy_curate.log
```

Run focused host tests:

```bash
/tmp/franklinflyers-testenv/bin/python -m pytest -q tests/test_aldi.py
/tmp/franklinflyers-testenv/bin/python -m pytest -q tests/test_big_y.py
```

Use the project venv at `/tmp/franklinflyers-testenv`; install `requirements.txt`, `pytest`, and `pytest-asyncio` there. Keep permanent tests in `tests/`, not in root-level probe scripts.

## Operational Checks

- After a live scraper run, inspect the latest `StoreDataset` status, item count, error, and sample `StoreDeal` rows.
- After event-source changes, verify `/events` and confirm source badges link to real calendars, not `#`.
- After template changes, check the rendered page at desktop and narrow widths; avoid absolute positioning for variable-length event text.
- If a source changes its HTML or blocks requests, prefer a structured feed/API or direct browser extraction before adding AI.
- Do not delete old valid data just because a new scrape failed.
- Verify that rendered public pages and published snapshots contain zero mock listings, dummy text, or placeholder evaluations.
