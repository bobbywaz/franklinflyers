# Franklin Flyers Agent Notes

This file is the fast handoff for future AI/code agents. Read this before making changes.

## Project Shape

- Stack: FastAPI + Jinja templates + SQLite + Playwright + Gemini.
- Primary runtime path: Docker Compose.
- Repo root DB file: `franklin_flyers.db`
- App entrypoint: `app/main.py`
- Container port mapping: host `8001` -> container `8000`

## Current Mental Model

- Scrapers are now persisted independently.
- `store_datasets` is the source of truth for the latest successful or failed attempt per scraper.
- Public homepage analysis is still published as combined snapshots in `runs` and related tables.
- A failed scraper rerun should not wipe prior valid store data.
- Grocery datasets stay active until the flyer validity window ends.
- Gas is independent and only shows on the homepage when populated.
- Admin is session-protected. Do not assume the old per-action password flow still exists.

## Important Files

- `app/main.py`
  - FastAPI routes, admin login, homepage/admin context building.
- `app/scheduler.py`
  - Full runs, single runs, dataset persistence, published snapshot generation, dynamic refresh jobs.
- `app/manager.py`
  - Scraper registry and Playwright execution.
- `app/store_utils.py`
  - Date parsing, validity windows, active dataset lookups, shared grocery/gas result normalization.
- `app/models.py`
  - Legacy snapshot tables plus current `StoreDataset`, `StoreDeal`, `StoreGasPrice`, `PublishedSnapshotStore`.
- `app/scrapers/`
  - Store-specific scraping behavior.
- `templates/admin.html`
  - Admin cards show `Items Scraped` and `Deals`.
- `templates/index.html`
  - Public homepage; gas section should only render when there is gas data.
- `tests/`
  - Permanent automated test suite.
  - New regression tests should be added here, not as one-off scripts in the repo root.

## Current Admin Behavior

- `/admin` requires login.
- Session auth uses Starlette `SessionMiddleware`.
- Login password is stored in the `configurations` table under `admin_password`.
- The admin dashboard has:
  - a `Full Run` play card first
  - one play card per scraper after that
  - separate `public_status` and `latest_status`
  - `Items Scraped` and `Deals` as separate metrics

## Scraper Registry

Current keys in `ScraperManager`:

- `aldi`
- `big_y`
- `food_city`
- `stop_and_shop`
- `fosters`
- `gas`

There is also a synthetic admin card for `full_run`.

## Data Model Notes

### Store-level persistence

Use these tables for per-scraper state:

- `store_datasets`
- `store_deals`
- `store_gas_prices`

Key `store_datasets` meanings:

- `status`
  - `success` or `failed`
- `item_count`
  - deal count shown publicly
- `items_scraped_count`
  - broader count of flyer items seen/read when available
- `flyer_start_date` / `flyer_end_date`
  - grocery flyer validity window
- `expires_at`
  - when public use of that dataset ends
- `next_refresh_at`
  - next scheduled refresh target

### Published homepage snapshots

These tables still matter for homepage combined analysis:

- `runs`
- `deals`
- `best_stores`
- `published_snapshot_stores`

Interpretation:

- `runs` is not the raw scraper-attempt history anymore.
- `runs` is the published combined homepage analysis snapshot.

## How To Run

### Start the app

```bash
cd /mnt/docker/franklinflyers
docker compose up -d --build
```

### Watch logs

```bash
cd /mnt/docker/franklinflyers
docker compose logs -f web
```

### Run one scraper from the terminal

```bash
cd /mnt/docker/franklinflyers
docker compose exec -T web python - <<'PY'
import asyncio
from app.scheduler import run_single_scrape
asyncio.run(run_single_scrape("big_y", trigger_mode="manual_single"))
PY
```

### Run a full scrape from the terminal

```bash
cd /mnt/docker/franklinflyers
docker compose exec -T web python - <<'PY'
import asyncio
from app.scheduler import run_full_scrape
asyncio.run(run_full_scrape(trigger_mode="manual_full"))
PY
```

### Run focused tests

```bash
cd /mnt/docker/franklinflyers
/tmp/franklinflyers-testenv/bin/python -m pytest -q tests/test_big_y.py
```

### Test file placement

- Keep permanent tests in `tests/`.
- Prefer names like `tests/test_<feature>.py`.
- Do not leave temporary scraper probes or debug runners in the repo root.
- If an exploratory script is needed during debugging, remove it before finishing unless the user explicitly wants it kept.

## Current Scraper Notes

### ALDI

- Uses Flipp.
- Requires ZIP/store selection before flyer extraction.
- Still uses screenshot/Gemini extraction rather than direct text extraction.

### Big Y

- This scraper was converted away from screenshot OCR.
- It now works by:
  - getting cookies/UA from FlareSolverr
  - calling Big Y store APIs to resolve and activate the Greenfield store
  - opening the weekly ad Flipp view
  - reading `button.item-overlay` `aria-label` text from the `Main Panel` iframe
- Important Big Y details:
  - ZIP used for search is `01376`
  - Greenfield store returned by Big Y APIs has ZIP `01301`
  - `wait_until="commit"` is required for `https://www.bigy.com/weeklyad/flyerview`
    - `domcontentloaded` was hanging even when the page was usable
  - `items_scraped_count` should come from readable overlay count, not deduped deals
  - Big Y creates its own browser page inside `scrape()`
    - this is intentional
    - the manager's default browser context UA caused Cloudflare failures in normal runs
- Verified working state:
  - Big Y produced roughly `291` deals from `292` readable flyer items
  - flyer dates were extracted as `2026-04-30` to `2026-05-06`

### Food City

- Flyer is a PDF.
- Current path downloads the PDF and sends it to Gemini.
- Likely candidate for future direct text extraction from embedded PDF text.

### Foster's

- Flyer is also a PDF.
- Current path downloads the PDF and sends it to Gemini.
- Also a candidate for future direct text extraction.

### Stop & Shop

- Current working path is Backflipp API first for `postal_code=01376` and query `Stop And Shop`.
- The API path avoids the live Stop & Shop weekly-ad DataDome challenge that currently blocks browser extraction.
- It should target the Greenfield weekly ad with `storeCode=0442`.
- Browser extraction is now a fallback only:
  - it reads `button.item-overlay` `aria-label` text from the `Main Panel` iframe
  - it currently remains vulnerable to CAPTCHA / anti-bot blocking
- Current blocker is still CAPTCHA / anti-bot access, not flyer text extraction.

### Gas

- Independent from grocery publishing.
- Freshness window is 24 hours.
- Public homepage should not render the gas section if there is no gas data.

## Scheduling / Publishing Rules

- Full scheduled runs are still the main way the homepage analysis is republished.
- Single-store runs update store-level datasets.
- A successful single-store run can repair public data when a store was missing.
- Do not let a failed new scrape erase older still-valid data for the same store.
- Grocery refresh timing is validity-aware:
  - next refresh usually targets one day before flyer expiration

## Operational Pitfalls

- The README still contained outdated instructions before this handoff file was added.
- Old `curl /api/refresh?pin=...` guidance is not the preferred admin path anymore.
- Session auth requires `itsdangerous` in the environment.
- Python 3.11 is the intended runtime now.
- Big Y and ALDI are the most layout-sensitive scrapers.

## Recommended Next Improvements

- Move PDF-based stores from Gemini-only extraction to direct PDF text extraction first, with Gemini as fallback.
- Replace deprecated `google.generativeai` with `google.genai`.
- Refresh README examples so they match current admin/session behavior exactly.
- Remove or archive root-level debugging screenshots once they are no longer useful.

## Maintenance Rule

When behavior changes, update this file in the same PR/commit. Treat it like architecture documentation, not a scratchpad.
