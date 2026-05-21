import datetime
import json
import logging
import re
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func

from .models import PublishedSnapshotStore, Run, StoreDataset

logger = logging.getLogger(__name__)

DATE_PATTERNS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%m-%d-%y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%B %d",
    "%b %d",
    "%m/%d",
    "%m-%d",
)

GROCERY_KIND = "grocery"
GAS_KIND = "gas"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def end_of_day(value: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(value, datetime.time(23, 59, 59))


def format_date_range(start: Optional[datetime.date], end: Optional[datetime.date]) -> str:
    if not start or not end:
        return ""
    return f"{start.month}/{start.day}-{end.month}/{end.day}"


def compute_grocery_schedule(flyer_end_date: datetime.date, now: Optional[datetime.datetime] = None) -> Tuple[datetime.datetime, datetime.datetime]:
    now = now or utcnow()
    expires_at = end_of_day(flyer_end_date)
    next_refresh_at = expires_at - datetime.timedelta(days=1)
    if next_refresh_at <= now:
        next_refresh_at = now + datetime.timedelta(minutes=5)
    return expires_at, next_refresh_at


def compute_gas_schedule(now: Optional[datetime.datetime] = None) -> Tuple[datetime.datetime, datetime.datetime]:
    now = now or utcnow()
    expires_at = now + datetime.timedelta(hours=24)
    next_refresh_at = now + datetime.timedelta(hours=23)
    return expires_at, next_refresh_at


def guess_flyer_dates(scraped_at: Optional[datetime.datetime] = None) -> Tuple[datetime.date, datetime.date]:
    scraped_at = scraped_at or utcnow()
    start_date = scraped_at.date()
    end_date = start_date + datetime.timedelta(days=6)
    return start_date, end_date


def parse_gemini_json(text: str):
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
    return json.loads(cleaned)


def parse_int_value(value, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    match = re.search(r"\d+", str(value))
    if not match:
        return default
    return int(match.group(0))


def parse_date_value(value, reference_date: Optional[datetime.date] = None) -> Optional[datetime.date]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value

    reference_date = reference_date or utcnow().date()
    text = str(value).strip()
    if not text:
        return None

    for pattern in DATE_PATTERNS:
        try:
            parsed = datetime.datetime.strptime(text, pattern)
            if "%Y" not in pattern and "%y" not in pattern:
                parsed = parsed.replace(year=reference_date.year)
                if parsed.date() < reference_date - datetime.timedelta(days=180):
                    parsed = parsed.replace(year=reference_date.year + 1)
            return parsed.date()
        except ValueError:
            continue

    return None


def parse_date_range_text(value: str, reference_date: Optional[datetime.date] = None) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    if not value:
        return None, None

    reference_date = reference_date or utcnow().date()
    text = value.strip()

    mmdd_matches = re.findall(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", text)
    if len(mmdd_matches) >= 2:
        start = _date_from_match(mmdd_matches[0], reference_date)
        end = _date_from_match(mmdd_matches[1], reference_date)
        return start, end

    text = re.sub(r"\b(valid|through|thru|from|to|until|-)\b", " ", text, flags=re.IGNORECASE)
    month_name_matches = re.findall(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?)",
        text,
        flags=re.IGNORECASE,
    )
    if len(month_name_matches) >= 2:
        start = parse_date_value(month_name_matches[0], reference_date)
        end = parse_date_value(month_name_matches[1], reference_date)
        return start, end

    return None, None


def normalize_grocery_analysis(result, scraped_at: Optional[datetime.datetime] = None) -> Dict:
    scraped_at = scraped_at or utcnow()
    reference_date = scraped_at.date()
    date_source = "guessed"
    deals: List[Dict] = []
    flyer_start = None
    flyer_end = None
    items_scraped_count = 0

    if isinstance(result, list):
        deals = result
    elif isinstance(result, dict):
        deals = result.get("deals") or result.get("items") or []
        items_scraped_count = parse_int_value(
            result.get("items_scraped")
            or result.get("items_scraped_count")
            or result.get("total_items_scraped")
            or result.get("items_seen")
            or result.get("total_items_seen"),
            default=0,
        )
        flyer_start = parse_date_value(result.get("flyer_start_date") or result.get("start_date"), reference_date)
        flyer_end = parse_date_value(result.get("flyer_end_date") or result.get("end_date"), reference_date)

        if not flyer_start or not flyer_end:
            text_candidates = [
                result.get("flyer_date_range"),
                result.get("date_range"),
                result.get("valid_dates"),
                result.get("dates"),
            ]
            for candidate in text_candidates:
                flyer_start, flyer_end = parse_date_range_text(str(candidate or ""), reference_date)
                if flyer_start and flyer_end:
                    break

        if flyer_start and flyer_end:
            date_source = "extracted"

    if not flyer_start or not flyer_end:
        flyer_start, flyer_end = guess_flyer_dates(scraped_at)

    if flyer_end < flyer_start:
        flyer_end = flyer_start

    if items_scraped_count <= 0:
        items_scraped_count = len(deals)

    expires_at, next_refresh_at = compute_grocery_schedule(flyer_end, scraped_at)
    return {
        "deals": deals,
        "items_scraped_count": items_scraped_count,
        "flyer_start_date": flyer_start,
        "flyer_end_date": flyer_end,
        "expires_at": expires_at,
        "next_refresh_at": next_refresh_at,
        "date_source": date_source,
    }


def build_grocery_result(scraper_key: str, store_name: str, result, scraped_at: Optional[datetime.datetime] = None) -> Dict:
    scraped_at = scraped_at or utcnow()
    normalized = normalize_grocery_analysis(result, scraped_at)
    normalized.update(
        {
            "scraper_key": scraper_key,
            "store_name": store_name,
            "kind": GROCERY_KIND,
            "scraped_at": scraped_at,
        }
    )
    return normalized


def build_gas_result(scraper_key: str, store_name: str, prices: List[Dict], scraped_at: Optional[datetime.datetime] = None) -> Dict:
    scraped_at = scraped_at or utcnow()
    expires_at, next_refresh_at = compute_gas_schedule(scraped_at)
    return {
        "scraper_key": scraper_key,
        "store_name": store_name,
        "kind": GAS_KIND,
        "scraped_at": scraped_at,
        "prices": prices,
        "items_scraped_count": len(prices),
        "expires_at": expires_at,
        "next_refresh_at": next_refresh_at,
    }


def active_dataset_subquery(db, kind: str, now: Optional[datetime.datetime] = None):
    now = now or utcnow()
    return (
        db.query(
            StoreDataset.scraper_key,
            func.max(StoreDataset.finished_at).label("finished_at"),
        )
        .filter(
            StoreDataset.kind == kind,
            StoreDataset.status == STATUS_SUCCESS,
            StoreDataset.expires_at != None,
            StoreDataset.expires_at >= now,
        )
        .group_by(StoreDataset.scraper_key)
        .subquery()
    )


def get_active_grocery_datasets(db, now: Optional[datetime.datetime] = None) -> List[StoreDataset]:
    subquery = active_dataset_subquery(db, GROCERY_KIND, now)
    return (
        db.query(StoreDataset)
        .join(
            subquery,
            (StoreDataset.scraper_key == subquery.c.scraper_key)
            & (StoreDataset.finished_at == subquery.c.finished_at),
        )
        .order_by(StoreDataset.store_name.asc())
        .all()
    )


def get_active_dataset_by_key(db, scraper_key: str, now: Optional[datetime.datetime] = None) -> Optional[StoreDataset]:
    now = now or utcnow()
    return (
        db.query(StoreDataset)
        .filter(
            StoreDataset.scraper_key == scraper_key,
            StoreDataset.status == STATUS_SUCCESS,
            StoreDataset.expires_at != None,
            StoreDataset.expires_at >= now,
        )
        .order_by(StoreDataset.finished_at.desc())
        .first()
    )


def get_latest_attempt_by_key(db, scraper_key: str) -> Optional[StoreDataset]:
    return (
        db.query(StoreDataset)
        .filter(StoreDataset.scraper_key == scraper_key)
        .order_by(StoreDataset.finished_at.desc(), StoreDataset.id.desc())
        .first()
    )


def get_latest_active_gas_dataset(db, now: Optional[datetime.datetime] = None) -> Optional[StoreDataset]:
    now = now or utcnow()
    return (
        db.query(StoreDataset)
        .filter(
            StoreDataset.scraper_key == "gas",
            StoreDataset.status == STATUS_SUCCESS,
            StoreDataset.expires_at != None,
            StoreDataset.expires_at >= now,
        )
        .order_by(StoreDataset.finished_at.desc())
        .first()
    )


def snapshot_active_scraper_keys(db, run: Optional[Run], now: Optional[datetime.datetime] = None) -> Tuple[Run, set]:
    if run is None:
        return None, set()
    now = now or utcnow()
    active_keys = {
        dataset.scraper_key
        for dataset in get_active_grocery_datasets(db, now)
    }
    published_keys = {row.scraper_key for row in run.published_stores}
    return run, active_keys.intersection(published_keys)


def snapshot_has_missing_store(db, run: Optional[Run], now: Optional[datetime.datetime] = None) -> bool:
    if run is None:
        return True
    _, active_keys = snapshot_active_scraper_keys(db, run, now)
    published_keys = {row.scraper_key for row in run.published_stores}
    return active_keys != published_keys


def should_include_snapshot_store(scraper_key: str, active_keys: Iterable[str]) -> bool:
    return scraper_key in set(active_keys)


def _date_from_match(match: Tuple[str, str, str], reference_date: datetime.date) -> Optional[datetime.date]:
    month, day, year = match
    year_value = reference_date.year
    if year:
        year_value = int(year)
        if year_value < 100:
            year_value += 2000
    try:
        return datetime.date(year_value, int(month), int(day))
    except ValueError:
        return None
