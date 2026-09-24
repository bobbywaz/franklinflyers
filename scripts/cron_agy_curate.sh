#!/usr/bin/env bash
set -eo pipefail

export HOME="/home/b"
export USER="b"
export PATH="/home/b/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

WORKDIR="/mnt/docker/franklinflyers"
LOG_DIR="$WORKDIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/agy_curate.log"

# Rotate log if larger than 10MB
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 10485760 ]; then
    mv "$LOG_FILE" "${LOG_FILE}.old"
fi

LOCK_FILE="/tmp/franklinflyers_agy_curate.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date -u '+%Y-%m-%d %H:%M:%SZ')] Another agy curation job is already running. Skipping." >> "$LOG_FILE"
    exit 0
fi

echo "========================================================" >> "$LOG_FILE"
echo "Starting automated Antigravity (agy) curation: $(date -u '+%Y-%m-%d %H:%M:%SZ')" >> "$LOG_FILE"
echo "========================================================" >> "$LOG_FILE"

cd "$WORKDIR"

# Run agy non-interactively using the host Antigravity subscription
/home/b/.local/bin/agy -p "In /mnt/docker/franklinflyers:
1. Groceries: Inspect the active grocery datasets in franklin_flyers.db (aldi, big_y, food_city, fosters, stop_and_shop). If any is expired or missing, trigger its single scraper once:
   docker compose exec -T web python -c 'import asyncio; from app.scheduler import run_single_scrape; asyncio.run(run_single_scrape(\"<key>\", trigger_mode=\"manual_single\"))'
   Then publish a fresh curated grocery snapshot using:
   docker compose exec -T web python -c 'import asyncio; from app.database import SessionLocal; from app.scheduler import _publish_active_grocery_snapshot; async def r(): db=SessionLocal(); await _publish_active_grocery_snapshot(db, trigger_mode=\"agy_cron\", failed_by_store={}); db.commit(); db.close(); asyncio.run(r())'
   Confirm the latest published run has status ready, contains all genuine high-value deals (score >= 8, zero filler score <= 6) without an artificial cap, and zero mock text exists.
2. Weed / Dispensaries: Inspect active dispensary datasets (patriot_care, rise_dispensary, leaf_joy, heirloom_collection, pharmacy_257, smokey_leaf, cheech_and_chong). If any is expired or missing, trigger its single scraper once using run_single_scrape(\"<key>\", trigger_mode=\"manual_single\").
3. Pharmacies: Inspect active pharmacy datasets (cvs_greenfield, walgreens_greenfield, walgreens_turners_falls). If any is expired or missing, trigger its single scraper once using run_single_scrape(\"<key>\", trigger_mode=\"manual_single\"). Ensure the cached pharmacy AI analysis in configurations is up to date and uncapped.
4. Verify http://localhost:8001/ (groceries), http://localhost:8001/dispensaries, and http://localhost:8001/pharmacies all return HTTP 200 with genuine uncapped deals and zero paid Gemini API calls.
Print a concise 3-line summary of the result." --dangerously-skip-permissions >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "========================================================" >> "$LOG_FILE"
echo "Finished at $(date -u '+%Y-%m-%d %H:%M:%SZ') with exit code $EXIT_CODE" >> "$LOG_FILE"
echo "========================================================" >> "$LOG_FILE"
exit $EXIT_CODE
