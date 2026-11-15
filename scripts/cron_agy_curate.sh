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
NOTE: Franklin Flyers runs under K3s Kubernetes (deployment/franklinflyers, container 'web' on node 'c'). Never touch or open franklin_flyers.db directly on the host while the pod is running to prevent SQLite WAL split-brain over NFS. Always run all checks, scrapers, and snapshot publications inside the pod via kubectl exec:

1. Groceries: Inspect active grocery datasets via:
   kubectl exec -n default deployment/franklinflyers -c web -- python -c 'from app.database import SessionLocal; from app.store_utils import get_active_grocery_datasets; db=SessionLocal(); print([(d.scraper_key, d.item_count, d.status) for d in get_active_grocery_datasets(db)]); db.close()'
   If any is expired or missing, trigger its single scraper once:
   kubectl exec -n default deployment/franklinflyers -c web -- python -c 'import asyncio; from app.scheduler import run_single_scrape; asyncio.run(run_single_scrape(\"<key>\", trigger_mode=\"manual_single\"))'
   Then publish a fresh curated grocery snapshot using:
   kubectl exec -n default deployment/franklinflyers -c web -- python -c 'import asyncio; from app.database import SessionLocal; from app.scheduler import _publish_active_grocery_snapshot; db=SessionLocal(); asyncio.run(_publish_active_grocery_snapshot(db, trigger_mode=\"agy_cron\", failed_by_store={})); db.commit(); db.close()'
   Confirm the latest published run has status ready, contains all genuine high-value deals (score >= 8, zero filler score <= 6) without an artificial cap, and zero mock text exists.
2. Weed / Dispensaries: Inspect active dispensary datasets (patriot_care, rise_dispensary, leaf_joy, heirloom_collection, pharmacy_257, smokey_leaf, cheech_and_chong). If any is expired or missing, trigger its single scraper once using run_single_scrape(\"<key>\", trigger_mode=\"manual_single\") via kubectl exec.
3. Pharmacies: Inspect active pharmacy datasets (cvs_greenfield, walgreens_greenfield, walgreens_turners_falls). If any is expired or missing, trigger its single scraper once using run_single_scrape(\"<key>\", trigger_mode=\"manual_single\") via kubectl exec. Ensure the cached pharmacy AI analysis in configurations is up to date and uncapped.
4. Events & Movies: Inspect active event datasets (shea_theater, rendezvous, tree_house, northampton_live, four_phantoms, franklin_chamber, shelburne_falls, visit_greenfield, river_culture, drake_amherst, iron_horse, luthiers_coop, marigold_theater, incandescent_brewing) and movie datasets (greenfield_garden_cinemas, cinemark_hadley). If stale or missing, trigger run_events_scrape() or run_movies_scrape() via kubectl exec.
5. Verify NodePort 30801 endpoints: http://10.168.3.58:30801/ (groceries), /dispensaries, /pharmacies, /events, and /movies all return HTTP 200 with genuine uncapped listings, robust weekend events, and zero paid Gemini API calls.
Print a concise 3-line summary of the result." --dangerously-skip-permissions >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "========================================================" >> "$LOG_FILE"
echo "Finished at $(date -u '+%Y-%m-%d %H:%M:%SZ') with exit code $EXIT_CODE" >> "$LOG_FILE"
echo "========================================================" >> "$LOG_FILE"
exit $EXIT_CODE
