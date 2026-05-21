import datetime
import json
import logging
import os
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .database import SessionLocal
from .gemini_analyzer import GeminiAnalyzer
from .manager import ScraperManager
from .models import (
    BestStore,
    Deal,
    FailedScrape,
    PublishedSnapshotStore,
    Run,
    StoreDataset,
    StoreDeal,
    StoreGasPrice,
)
from .store_utils import (
    GAS_KIND,
    GROCERY_KIND,
    STATUS_FAILED,
    STATUS_SUCCESS,
    compute_gas_schedule,
    compute_grocery_schedule,
    get_active_dataset_by_key,
    get_active_grocery_datasets,
    get_latest_active_gas_dataset,
    guess_flyer_dates,
    utcnow,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_scheduler: Optional[AsyncIOScheduler] = None

SCRAPER_KEY_BY_STORE_NAME = {
    "ALDI": "aldi",
    "Big Y": "big_y",
    "Food City": "food_city",
    "Stop & Shop": "stop_and_shop",
    "Foster's": "fosters",
}


async def run_scrape_and_analyze():
    await run_full_scrape(trigger_mode="scheduled_full")


async def run_full_scrape(trigger_mode: str = "scheduled_full") -> Optional[Run]:
    logger.info("--- STARTING FULL SCRAPE JOB (%s) ---", trigger_mode)
    manager = ScraperManager()
    results = await manager.run_full_batch(run_date=utcnow().strftime("%Y-%m-%d %H:%M"))

    db = SessionLocal()
    try:
        failed_by_store = {}
        for result in results:
            persisted = _persist_scrape_result(db, result, trigger_mode)
            if persisted.status == STATUS_FAILED:
                failed_by_store[persisted.store_name] = persisted.error_message or "Scrape failed"

        db.flush()
        published_run = await _publish_active_grocery_snapshot(
            db,
            trigger_mode=trigger_mode,
            failed_by_store=failed_by_store,
        )
        db.commit()
        _sync_dynamic_refresh_jobs()
        return published_run
    except Exception as e:
        db.rollback()
        logger.error("FATAL ERROR in full scrape job: %s", e, exc_info=True)
        return None
    finally:
        db.close()


async def run_single_scrape(scraper_key: str, trigger_mode: str = "manual_single") -> Optional[StoreDataset]:
    logger.info("--- STARTING SINGLE SCRAPE JOB for %s (%s) ---", scraper_key, trigger_mode)
    check_db = SessionLocal()
    try:
        had_active_before = get_active_dataset_by_key(check_db, scraper_key) is not None
    finally:
        check_db.close()

    manager = ScraperManager()
    result = await manager.run_single(scraper_key, run_date=utcnow().strftime("%Y-%m-%d %H:%M"))

    db = SessionLocal()
    try:
        persisted = _persist_scrape_result(db, result, trigger_mode)
        if (
            persisted.status == STATUS_SUCCESS
            and persisted.kind == GROCERY_KIND
            and not had_active_before
        ):
            db.flush()
            await _publish_active_grocery_snapshot(
                db,
                trigger_mode=f"{trigger_mode}_repair_publish",
                failed_by_store={},
            )
        db.commit()
        _sync_dynamic_refresh_jobs()
        return persisted
    except Exception as e:
        db.rollback()
        logger.error("FATAL ERROR in single scrape job for %s: %s", scraper_key, e, exc_info=True)
        return None
    finally:
        db.close()


def start_scheduler():
    global _scheduler

    bootstrap_store_data()

    scheduler = AsyncIOScheduler()
    cron_expr = os.getenv("SCRAPE_SCHEDULE", "0 2 * * 1,4")
    scheduler.add_job(
        run_full_scrape,
        CronTrigger.from_crontab(cron_expr),
        kwargs={"trigger_mode": "scheduled_full"},
        id="scheduled_full_run",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    _sync_dynamic_refresh_jobs()
    logger.info("Scheduler started with cron: %s", cron_expr)
    return scheduler


def bootstrap_store_data():
    db = SessionLocal()
    try:
        if db.query(StoreDataset).count() == 0:
            latest_run = (
                db.query(Run)
                .filter(Run.is_ready == True)
                .order_by(Run.run_date.desc())
                .first()
            )
            if latest_run:
                logger.info("Backfilling store datasets from latest published snapshot run %s", latest_run.id)
                _backfill_from_legacy_run(db, latest_run)
                db.commit()

        latest_run = (
            db.query(Run)
            .filter(Run.is_ready == True)
            .order_by(Run.run_date.desc())
            .first()
        )
        if latest_run and not latest_run.published_stores:
            _backfill_published_store_links(db, latest_run)
            db.commit()
    finally:
        db.close()


def _persist_scrape_result(db, result: Dict, trigger_mode: str) -> StoreDataset:
    now = utcnow()
    previous_active = get_active_dataset_by_key(db, result["scraper_key"], now)

    dataset = StoreDataset(
        scraper_key=result["scraper_key"],
        store_name=result["store_name"],
        kind=result["kind"],
        trigger_mode=trigger_mode,
        status=result["status"],
        started_at=now,
        finished_at=now,
        item_count=0,
        items_scraped_count=0,
        error_message=result.get("error_message"),
    )
    db.add(dataset)
    db.flush()

    if result["status"] == STATUS_SUCCESS and result.get("payload"):
        payload = result["payload"]
        dataset.flyer_start_date = payload.get("flyer_start_date")
        dataset.flyer_end_date = payload.get("flyer_end_date")
        dataset.expires_at = payload.get("expires_at")
        dataset.next_refresh_at = payload.get("next_refresh_at")
        dataset.date_source = payload.get("date_source")
        dataset.item_count = payload.get("item_count", 0)
        dataset.items_scraped_count = payload.get("items_scraped_count", dataset.item_count)

        if dataset.kind == GROCERY_KIND:
            for deal in payload.get("deals", []):
                db.add(
                    StoreDeal(
                        dataset_id=dataset.id,
                        item_name=deal.get("name", ""),
                        sale_price=deal.get("price", ""),
                        description=deal.get("description", ""),
                    )
                )
        else:
            for price in payload.get("prices", []):
                db.add(
                    StoreGasPrice(
                        dataset_id=dataset.id,
                        station_name=price.get("station_name", ""),
                        address=price.get("address", ""),
                        city=price.get("city", ""),
                        price=price.get("price", ""),
                        fuel_type=price.get("fuel_type", ""),
                        updated_at=price.get("updated_at", ""),
                        source_updated_at=price.get("source_updated_at", ""),
                    )
                )
    elif previous_active and previous_active.expires_at and previous_active.expires_at > now:
        retry_hours = int(os.getenv("SCRAPE_RETRY_HOURS", "6"))
        retry_at = min(previous_active.expires_at, now + datetime.timedelta(hours=retry_hours))
        if retry_at > now:
            previous_active.next_refresh_at = retry_at

    return dataset


async def _publish_active_grocery_snapshot(db, trigger_mode: str, failed_by_store: Dict[str, str]) -> Optional[Run]:
    active_datasets = get_active_grocery_datasets(db)
    if not active_datasets:
        logger.warning("No active grocery datasets were available to publish")
        return None

    all_deals = []
    for dataset in active_datasets:
        for deal in dataset.deals:
            all_deals.append(
                {
                    "store_name": dataset.store_name,
                    "name": deal.item_name,
                    "price": deal.sale_price,
                    "description": deal.description or "",
                }
            )

    if not all_deals:
        logger.warning("Active grocery datasets contained no deals to publish")
        return None

    analyzer = GeminiAnalyzer()
    analysis = await analyzer.analyze_deals(all_deals)

    new_run = Run(run_date=utcnow(), is_ready=False)
    db.add(new_run)
    db.flush()

    if analysis.get("seasonal_guide"):
        new_run.seasonal_info = json.dumps(analysis["seasonal_guide"])
    if analysis.get("recipe_idea"):
        new_run.recipe_idea = json.dumps(analysis["recipe_idea"])

    best_store_name = None
    if analysis.get("best_store"):
        best_store = analysis["best_store"]
        best_store_name = best_store.get("store_name")
        strengths = best_store.get("strengths", "")
        if isinstance(strengths, list):
            strengths = "\n".join(strengths)
        weaknesses = best_store.get("weaknesses", "")
        if isinstance(weaknesses, list):
            weaknesses = "\n".join(weaknesses)

        db.add(
            BestStore(
                run_id=new_run.id,
                store_name=best_store["store_name"],
                summary=best_store["summary"],
                strengths=strengths,
                weaknesses=weaknesses,
                score=best_store["score"],
            )
        )

    for scored_deal in analysis.get("scored_deals", []):
        if scored_deal.get("store_name") in failed_by_store and scored_deal.get("store_name") not in {
            dataset.store_name for dataset in active_datasets
        }:
            continue
        db.add(
            Deal(
                run_id=new_run.id,
                store_name=scored_deal["store_name"],
                item_name=scored_deal["item_name"],
                description=scored_deal.get("size", ""),
                sale_price=scored_deal["sale_price"],
                category=scored_deal["category"],
                score=scored_deal["score"],
                explanation=scored_deal["explanation"],
            )
        )

    for dataset in active_datasets:
        db.add(
            PublishedSnapshotStore(
                run_id=new_run.id,
                store_dataset_id=dataset.id,
                scraper_key=dataset.scraper_key,
                store_name=dataset.store_name,
            )
        )

    for store_name, error_message in failed_by_store.items():
        db.add(
            FailedScrape(
                run_id=new_run.id,
                store_name=store_name,
                error_message=error_message,
            )
        )

    if best_store_name:
        active_store_names = {dataset.store_name for dataset in active_datasets}
        if best_store_name not in active_store_names:
            logger.info("Best store %s was not active; leaving best-store section empty", best_store_name)

    new_run.is_ready = True
    logger.info("Published new homepage snapshot run %s from %s active stores", new_run.id, len(active_datasets))
    return new_run


def _sync_dynamic_refresh_jobs():
    if _scheduler is None:
        return

    db = SessionLocal()
    try:
        manager = ScraperManager()
        for card in manager.list_scrapers():
            scraper_key = card["scraper_key"]
            if scraper_key == "full_run":
                continue

            job_id = f"refresh_{scraper_key}"
            dataset = get_active_dataset_by_key(db, scraper_key)
            if dataset is None and scraper_key == "gas":
                dataset = get_latest_active_gas_dataset(db)

            if dataset and dataset.next_refresh_at:
                _scheduler.add_job(
                    run_single_scrape,
                    DateTrigger(run_date=dataset.next_refresh_at),
                    kwargs={"scraper_key": scraper_key, "trigger_mode": "scheduled_refresh"},
                    id=job_id,
                    replace_existing=True,
                )
            else:
                existing = _scheduler.get_job(job_id)
                if existing:
                    existing.remove()
    finally:
        db.close()


def _backfill_from_legacy_run(db, latest_run: Run):
    deals_by_store = {}
    for deal in latest_run.deals:
        deals_by_store.setdefault(deal.store_name, []).append(deal)

    for store_name, deals in deals_by_store.items():
        scraper_key = SCRAPER_KEY_BY_STORE_NAME.get(store_name)
        if not scraper_key:
            continue

        flyer_start_date, flyer_end_date = guess_flyer_dates(latest_run.run_date)
        expires_at, next_refresh_at = compute_grocery_schedule(flyer_end_date, latest_run.run_date)
        dataset = StoreDataset(
            scraper_key=scraper_key,
            store_name=store_name,
            kind=GROCERY_KIND,
            trigger_mode="backfill",
            status=STATUS_SUCCESS,
            started_at=latest_run.run_date,
            finished_at=latest_run.run_date,
            flyer_start_date=flyer_start_date,
            flyer_end_date=flyer_end_date,
            expires_at=expires_at,
            next_refresh_at=next_refresh_at,
            date_source="guessed",
            item_count=len(deals),
            items_scraped_count=len(deals),
        )
        db.add(dataset)
        db.flush()
        for deal in deals:
            db.add(
                StoreDeal(
                    dataset_id=dataset.id,
                    item_name=deal.item_name,
                    sale_price=deal.sale_price,
                    description=deal.description,
                )
            )

    if latest_run.gas_prices:
        expires_at, next_refresh_at = compute_gas_schedule(latest_run.run_date)
        gas_dataset = StoreDataset(
            scraper_key="gas",
            store_name="Gas Prices",
            kind=GAS_KIND,
            trigger_mode="backfill",
            status=STATUS_SUCCESS,
            started_at=latest_run.run_date,
            finished_at=latest_run.run_date,
            expires_at=expires_at,
            next_refresh_at=next_refresh_at,
            item_count=len(latest_run.gas_prices),
            items_scraped_count=len(latest_run.gas_prices),
            date_source="backfill",
        )
        db.add(gas_dataset)
        db.flush()
        for price in latest_run.gas_prices:
            db.add(
                StoreGasPrice(
                    dataset_id=gas_dataset.id,
                    station_name=price.station_name,
                    address=price.address,
                    city=price.city,
                    price=price.price,
                    fuel_type=price.fuel_type,
                    updated_at=price.updated_at,
                    source_updated_at=price.source_updated_at,
                )
            )

    _backfill_published_store_links(db, latest_run)


def _backfill_published_store_links(db, latest_run: Run):
    store_names = {deal.store_name for deal in latest_run.deals}
    for store_name in store_names:
        scraper_key = SCRAPER_KEY_BY_STORE_NAME.get(store_name)
        if not scraper_key:
            continue
        dataset = (
            db.query(StoreDataset)
            .filter(
                StoreDataset.scraper_key == scraper_key,
                StoreDataset.status == STATUS_SUCCESS,
            )
            .order_by(StoreDataset.finished_at.desc())
            .first()
        )
        db.add(
            PublishedSnapshotStore(
                run_id=latest_run.id,
                store_dataset_id=dataset.id if dataset else None,
                scraper_key=scraper_key,
                store_name=store_name,
            )
        )
