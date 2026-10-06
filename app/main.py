import json
import logging
import os
import datetime
import re
from typing import Dict, List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .database import SessionLocal, get_db, init_db
from .gemini_analyzer import GeminiAnalyzer, PHARMACY_CATEGORIES
from .manager import ScraperManager
from .models import Configuration, Run, StoreDataset
from .scheduler import run_full_scrape, run_grocery_scrape, run_single_scrape, start_scheduler
from .store_utils import (
    STATUS_SUCCESS,
    format_date_range,
    get_active_dataset_by_key,
    get_active_grocery_datasets,
    get_active_movie_datasets,
    get_active_pharmacy_datasets,
    get_latest_attempt_by_key,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STORE_FLYERS = {
    "ALDI": "https://info.aldi.us/weekly-specials/weekly-ads?zipCode=01376",
    "Big Y": "https://www.bigy.com/weekly-ad/flyerview",
    "Food City": "https://www.foodcitymkt.com/weekly-ad-1",
    "Stop & Shop": "https://stopandshop.com/weekly-ad?storeCode=0442",
    "Foster's": "https://www.fosterssupermarket.com/weekly-ad/",
}

app = FastAPI(title="Franklin Flyers")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("ADMIN_SESSION_SECRET", "franklin-flyers-admin-session"),
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup_event():
    init_db()

    db = SessionLocal()
    try:
        admin_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
        if not admin_pass:
            db.add(Configuration(key="admin_password", value="changeme"))
            db.commit()
            logger.info("Initialized default admin password 'changeme'")
    finally:
        db.close()

    app.state.scheduler = start_scheduler()


def _is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get("admin_authenticated"))


def _latest_success_by_key(db: Session, scraper_key: str) -> Optional[StoreDataset]:
    return (
        db.query(StoreDataset)
        .filter(
            StoreDataset.scraper_key == scraper_key,
            StoreDataset.status == STATUS_SUCCESS,
        )
        .order_by(StoreDataset.finished_at.desc(), StoreDataset.id.desc())
        .first()
    )


def _build_home_context(request: Request, db: Session):
    latest_run = db.query(Run).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()
    active_grocery_datasets = get_active_grocery_datasets(db)
    active_store_names = {dataset.store_name for dataset in active_grocery_datasets}

    active_store_badges = [
        {
            "name": dataset.store_name,
            "range_label": format_date_range(dataset.flyer_start_date, dataset.flyer_end_date),
            "scraper_key": dataset.scraper_key,
            "flyer_url": STORE_FLYERS.get(dataset.store_name, "#"),
        }
        for dataset in active_grocery_datasets
    ]

    top_overall = []
    deals_by_category = {}
    best_store = None
    seasonal_guide = None
    recipe_idea = None

    if latest_run:
        if latest_run.best_store and latest_run.best_store.store_name in active_store_names:
            best_store = latest_run.best_store

        if latest_run.seasonal_info:
            try:
                seasonal_guide = json.loads(latest_run.seasonal_info)
            except Exception:
                seasonal_guide = None

        if latest_run.recipe_idea:
            try:
                recipe_idea = json.loads(latest_run.recipe_idea)
            except Exception:
                recipe_idea = None

        published_deals = [deal for deal in latest_run.deals if deal.store_name in active_store_names]
        top_overall = sorted(published_deals, key=lambda deal: deal.score or 0, reverse=True)[:6]

        for deal in published_deals:
            deals_by_category.setdefault(deal.category, []).append(deal)

    return {
        "request": request,
        "has_data": bool(top_overall or deals_by_category or active_store_badges),
        "latest_run": latest_run,
        "best_store": best_store,
        "top_overall": top_overall,
        "deals_by_category": deals_by_category,
        "seasonal_guide": seasonal_guide,
        "recipe_idea": recipe_idea,
        "active_store_badges": active_store_badges,
    }


def _build_admin_context(request: Request, db: Session, message: str = None, error: str = None):
    manager = ScraperManager()
    latest_run = db.query(Run).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()
    cards = []
    latest_published_datasets = [entry.dataset for entry in latest_run.published_stores if entry.dataset] if latest_run else []

    for entry in manager.list_scrapers():
        scraper_key = entry["scraper_key"]
        if scraper_key in ("full_run", "grocery_run"):
            is_grocery = (scraper_key == "grocery_run")
            cards.append(
                {
                    "scraper_key": scraper_key,
                    "name": "All Groceries" if is_grocery else "Full Run",
                    "kind": "batch",
                    "public_status": "Published" if latest_run else "Missing",
                    "latest_status": "Ready" if latest_run else "Never Run",
                    "items_scraped_count": sum(dataset.items_scraped_count or dataset.item_count or 0 for dataset in latest_published_datasets),
                    "deal_count": len(latest_run.deals) if latest_run else 0,
                    "date_label": latest_run.run_date.strftime("%Y-%m-%d %H:%M UTC") if latest_run else "",
                    "next_refresh_at": None,
                    "last_error": None,
                }
            )
            continue

        latest_attempt = get_latest_attempt_by_key(db, scraper_key)
        latest_success = _latest_success_by_key(db, scraper_key)
        active_dataset = get_active_dataset_by_key(db, scraper_key)

        if active_dataset:
            public_status = "Active"
        elif latest_success:
            public_status = "Expired Hidden"
        else:
            public_status = "Missing"

        if latest_attempt:
            latest_status = latest_attempt.status.title()
        else:
            latest_status = "Never Run"

        date_label = ""
        if active_dataset and active_dataset.kind in ("grocery", "dispensary", "event", "movie"):
            date_label = format_date_range(active_dataset.flyer_start_date, active_dataset.flyer_end_date)
        elif latest_success and latest_success.kind in ("grocery", "dispensary", "event", "movie"):
            date_label = format_date_range(latest_success.flyer_start_date, latest_success.flyer_end_date)

        cards.append(
            {
                "scraper_key": scraper_key,
                "name": entry["store_name"],
                "kind": entry["kind"],
                "public_status": public_status,
                "latest_status": latest_status,
                "items_scraped_count": (
                    (active_dataset or latest_success).items_scraped_count
                    or (active_dataset or latest_success).item_count
                ) if (active_dataset or latest_success) else 0,
                "deal_count": (active_dataset or latest_success).item_count if (active_dataset or latest_success) else 0,
                "date_label": date_label,
                "next_refresh_at": active_dataset.next_refresh_at if active_dataset else None,
                "last_error": latest_attempt.error_message if latest_attempt and latest_attempt.status != STATUS_SUCCESS else None,
                "latest_run_at": latest_attempt.finished_at if latest_attempt else None,
            }
        )

    return {
        "request": request,
        "cards": cards,
        "message": message,
        "error": error,
    }


def _require_admin(request: Request):
    if not _is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="index.html", context=_build_home_context(request, db))


WEED_CATEGORIES = {
    "Flower": ("flower", "bud", "nug"),
    "Pre-rolls": ("pre-roll", "preroll", "joint", "dogwalker"),
    "Edibles": ("gummy", "edible", "chocolate", "tea", "beverage", "chew", "bar", "mint"),
    "Vapes": ("vape", "cart", "pod", "disposable", "elite"),
    "Concentrates": ("shatter", "resin", "wax", "crumble", "badder", "shatter", "rosin", "hash", "concentrate")
}

def categorize_weed(name: str, desc: str) -> str:
    text = f"{name} {desc}".lower()
    for cat, keywords in WEED_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            return cat
    return "Flower"

def get_discount_percentage(name: str, desc: str, price_str: str) -> float:
    import re
    combined = f"{name} {desc}".lower()

    # 1. BOGOs
    if "buy 1 get 1" in combined or "bogo" in combined:
        return 0.50
    if "buy 2 get 1" in combined:
        return 0.33

    # 2. Explicit percentage off
    pct_match = re.search(r"(\d{1,2})\s*%\s*(?:off|discount|savings)", combined)
    if pct_match:
        return float(pct_match.group(1)) / 100.0

    # 3. Regular vs sale price
    price_val = None
    reg_val = None
    price_match = re.search(r"\$(\d+(?:\.\d+)?)", price_str)
    if price_match:
        price_val = float(price_match.group(1))
    reg_match = re.search(r"(?:sale from|was|regular|reg|save)\s*\$(\d+(?:\.\d+)?)", combined)
    if reg_match:
        reg_val = float(reg_match.group(1))
    if price_val and reg_val and reg_val > price_val:
        return (reg_val - price_val) / reg_val

    return 0.0


def score_weed_deal(discount: float) -> int:
    """Score cannabis promotions strictly by value depth.
    10: BOGO / 50%+ off
    9: 30% - 49% off
    8: 20% - 29% off
    7: 15% - 19% off
    6: 10% - 14% off
    1-5: <10% off or regular menu price (filler)
    """
    if discount >= 0.50:
        return 10
    elif discount >= 0.30:
        return 9
    elif discount >= 0.20:
        return 8
    elif discount >= 0.15:
        return 7
    elif discount >= 0.10:
        return 6
    elif discount > 0.0:
        return 5
    return 1


@app.get("/dispensaries", response_class=HTMLResponse)
async def read_dispensaries(request: Request, db: Session = Depends(get_db)):
    from .store_utils import get_active_dispensary_datasets
    active_datasets = get_active_dispensary_datasets(db)

    all_deals = []
    store_deals_map = {}

    for dataset in active_datasets:
        store_deals_map[dataset.store_name] = []
        for deal in dataset.deals:
            category = categorize_weed(deal.item_name, deal.description or "")
            discount = get_discount_percentage(deal.item_name, deal.description or "", deal.sale_price)
            score = score_weed_deal(discount)

            deal_dict = {
                "id": deal.id,
                "store_name": dataset.store_name,
                "item_name": deal.item_name,
                "sale_price": deal.sale_price,
                "description": deal.description or "",
                "category": category,
                "score": score,
                "discount": discount,
            }
            all_deals.append(deal_dict)
            store_deals_map[dataset.store_name].append(deal_dict)

    # Filter for genuine deals: show all really good deals (score >= 8), 0 filler (score <= 6)
    good_deals = [d for d in all_deals if d["score"] >= 8]
    if not good_deals and all_deals:
        good_deals = [d for d in all_deals if d["score"] >= 7]

    # No hard cap! Show all genuine high-value deals sorted by discount depth
    top_overall = sorted(good_deals, key=lambda x: (x["score"], x["discount"]), reverse=True)

    deals_by_category = {}
    for deal in good_deals:
        deals_by_category.setdefault(deal["category"], []).append(deal)

    best_store = None
    if store_deals_map:
        store_stats = []
        for store_name, deals in store_deals_map.items():
            discounted = [d for d in deals if d["discount"] > 0]
            if discounted:
                avg_discount = sum(d["discount"] for d in discounted) / len(discounted)
                store_stats.append({
                    "store_name": store_name,
                    "avg_discount": avg_discount,
                    "deal_count": len(discounted),
                })
        if store_stats:
            best = max(store_stats, key=lambda x: x["avg_discount"])
            best_score = score_weed_deal(best["avg_discount"])
            best_store = {
                "store_name": best["store_name"],
                "score": best_score,
                "summary": f"{best['store_name']} offers the highest average savings of {int(best['avg_discount'] * 100)}% across {best['deal_count']} verified sale deals this week.",
                "strengths": "Deep promotional discounts on premium flower, concentrates, and vape cartridges.",
                "weaknesses": "Popular sale strains sell out quickly; online pre-ordering recommended.",
            }
            
    DISPENSARY_URLS = {
        "patriot_care": "https://www.patriotcare.org/shop/store/731/featured",
        "rise_dispensary": "https://risecannabis.com/dispensaries/massachusetts/greenfield/",
        "leaf_joy": "https://dutchie.com/stores/leaf-joy",
        "heirloom_collection": "https://theheirloomcollective.us/shop-bernardston/",
        "pharmacy_257": "https://shop.253farmacy.com/collection/flower",
        "smokey_leaf": "https://thesmokeyleaf.com/menu/",
        "cheech_and_chong": "https://greenfield.dispensoria.com/",
    }
    active_store_badges = [
        {
            "name": dataset.store_name,
            "range_label": format_date_range(dataset.flyer_start_date, dataset.flyer_end_date),
            "scraper_key": dataset.scraper_key,
            "flyer_url": DISPENSARY_URLS.get(dataset.scraper_key, "#")
        }
        for dataset in active_datasets
    ]
    
    context = {
        "request": request,
        "has_data": bool(all_deals),
        "best_store": best_store,
        "top_overall": top_overall,
        "deals_by_category": deals_by_category,
        "active_store_badges": active_store_badges
    }
    return templates.TemplateResponse(request=request, name="dispensaries.html", context=context)


def _get_upcoming_wheel_movies(
    db: Session,
    today: Optional[datetime.date] = None,
    max_hours_ahead: float = 2.5,
    max_movies: int = 8,
    now_ref: Optional[datetime.datetime] = None,
) -> List[Dict]:
    """Retrieve upcoming movie showtimes within the next few hours for the activity wheel.

    Args:
        db: Database session for querying active movie datasets.
        today: Reference date for valid datasets; defaults to Eastern local date.
        max_hours_ahead: Maximum hours into the future to look for starting showtimes (default 2.5h).
        max_movies: Maximum number of movie items to include on the wheel (default 8).
        now_ref: Optional explicit datetime used for testing; defaults to current Eastern time.

    Returns:
        List of movie activity dictionaries sorted by start time, deduplicated by title,
        and capped at max_movies.
    """
    import zoneinfo
    try:
        local_tz = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        local_tz = datetime.timezone.utc

    now_local = now_ref or datetime.datetime.now(local_tz)
    today = today or now_local.date()

    # Grace period: allow movies starting up to 10 minutes ago (previews/trailers buffer)
    min_dt = now_local - datetime.timedelta(minutes=10)
    # Strictly within the next few hours (no end-of-day / midnight expansion)
    max_dt = now_local + datetime.timedelta(hours=max_hours_ahead)

    from .store_utils import get_active_movie_datasets
    active_movie_datasets = get_active_movie_datasets(db)
    movie_items = []

    def parse_showtime_dt(t_str: str) -> Optional[datetime.datetime]:
        """Parse a 12-hour time string (e.g. '4:30 PM') into a datetime today."""
        m = re.search(r"(\d{1,2}):(\d{2})\s*([apAP])(?:[mM])?", t_str)
        if not m:
            return None
        h = int(m.group(1))
        minute = int(m.group(2))
        mer = m.group(3).upper()
        if mer == "P" and h < 12:
            h += 12
        elif mer == "A" and h == 12:
            h = 0
        return now_local.replace(hour=h, minute=minute, second=0, microsecond=0)

    for dataset in active_movie_datasets:
        # Check dataset validity window
        if dataset.flyer_start_date and dataset.flyer_end_date:
            if not (dataset.flyer_start_date <= today <= dataset.flyer_end_date):
                continue

        for deal in dataset.deals:
            raw_times = (deal.sale_price or "").split(",")
            upcoming_times = []
            for t in raw_times:
                t_clean = t.strip()
                if not t_clean or "Check schedule" in t_clean:
                    continue
                dt = parse_showtime_dt(t_clean)
                if dt and min_dt <= dt <= max_dt:
                    upcoming_times.append((dt, t_clean))

            if not upcoming_times:
                continue

            upcoming_times.sort(key=lambda x: x[0])
            next_dt, next_time = upcoming_times[0]
            other_times = [x[1] for x in upcoming_times[1:]]

            # Extract structured ticketing and details URLs
            ticket_url_match = re.search(r"Tickets:\s*(\S+)", deal.description or "")
            ticket_url = ticket_url_match.group(1) if ticket_url_match else ""

            details_url_match = re.search(r"Details:\s*(\S+)", deal.description or "")
            details_url = details_url_match.group(1) if details_url_match else (
                "https://www.gardencinemas.net/" if "Garden" in dataset.store_name else "https://www.cinemark.com/"
            )

            clean_desc = deal.description or ""
            clean_desc = re.sub(r"\s*\|\s*(?:Poster|Trailer|Tickets|Details):.*", "", clean_desc).strip()

            datetime_label = f"Starts at {next_time}"
            if other_times:
                datetime_label += f" • Also at {', '.join(other_times)}"

            movie_items.append({
                "id": f"movie-{deal.id}",
                "movie_deal_id": deal.id,
                "title": f"🎬 {deal.item_name}",
                "pure_title": deal.item_name,
                "store_name": dataset.store_name,
                "datetime_label": datetime_label,
                "next_time": next_time,
                "next_dt": next_dt,
                "description": clean_desc,
                "detail_url": details_url,
                "ticket_url": ticket_url,
                "movies_url": f"/movies#movie-{deal.id}",
                "is_movie": True,
            })

    # Sort nearest showtime first
    movie_items.sort(key=lambda m: m["next_dt"])

    # Deduplicate by normalized movie title so duplicate screenings across venues don't crowd the wheel
    seen_titles = set()
    deduped_movies = []
    for item in movie_items:
        norm = re.sub(r"[^\w\s]", "", item["pure_title"].lower()).strip()
        if norm not in seen_titles:
            seen_titles.add(norm)
            deduped_movies.append(item)

    if max_movies and max_movies > 0:
        return deduped_movies[:max_movies]
    return deduped_movies


def _interleave_wheel_items(events: List[Dict], movies: List[Dict]) -> List[Dict]:
    """Evenly distribute events and movies around the circular wheel canvas.

    Interleaves the two lists proportionally so that neither events nor movies
    are clumped into contiguous blocks on the wheel.
    """
    if not movies:
        return events
    if not events:
        return movies
    total = len(events) + len(movies)
    result = []
    e_idx, m_idx = 0, 0
    for i in range(total):
        if m_idx < len(movies) and (e_idx >= len(events) or (m_idx / len(movies)) <= (e_idx / len(events))):
            result.append(movies[m_idx])
            m_idx += 1
        else:
            result.append(events[e_idx])
            e_idx += 1
    return result


@app.get("/events", response_class=HTMLResponse)
async def read_events(request: Request, db: Session = Depends(get_db)):
    """Render the local events calendar and interactive random activity wheel.

    Queries active event datasets, computes calendar date matrix with recurring
    events expanded, fetches soonest upcoming movie showtimes within the next 2.5 hours,
    and renders the events view.
    """
    from .store_utils import get_active_event_datasets
    active_datasets = get_active_event_datasets(db)
    try:
        import zoneinfo
        local_tz = zoneinfo.ZoneInfo("America/New_York")
        today = datetime.datetime.now(local_tz).date()
    except Exception:
        today = datetime.datetime.now(datetime.timezone.utc).date()

    def parse_event_date(value):
        from .store_utils import parse_date_value

        text = re.sub(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+", "", value or "", flags=re.IGNORECASE)
        text = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", text)
        match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}(?:,\s*\d{4})?",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return parse_date_value(match.group(0), today)
        iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", value or "")
        if iso_match:
            try:
                return datetime.date.fromisoformat(iso_match.group(0))
            except ValueError:
                pass
        return None
    
    all_events = []
    store_events_map = {}
    
    for dataset in active_datasets:
        store_events_map[dataset.store_name] = []
        for deal in dataset.deals:
            event_label = (deal.sale_price or "").strip()
            description_label = deal.description.split("|", 1)[0].strip() if deal.description else ""
            event_date = parse_event_date(event_label)
            if not event_date and parse_event_date(description_label):
                event_label = description_label
                event_date = parse_event_date(event_label)
            elif not event_date and re.search(r"\b(?:am|pm)\b", description_label, re.IGNORECASE):
                if not re.search(r"\b(?:am|pm)\b", event_label, re.IGNORECASE):
                    event_label = f"{event_label} - {description_label}".strip(" -")
            if event_date and event_date < today:
                continue
            detail_url_match = re.search(r"Details:\s*(\S+)", deal.description or "")
            detail_url = detail_url_match.group(1) if detail_url_match else ""
            event_description = re.sub(r"\s*\|\s*Details:\s*\S+", "", deal.description or "").strip()
            event_dict = {
                "id": deal.id,
                "store_name": dataset.store_name,
                "title": deal.item_name,
                "datetime_label": event_label,
                "description": event_description,
                "event_date": event_date,
                "detail_url": detail_url,
            }
            all_events.append(event_dict)
            store_events_map[dataset.store_name].append(event_dict)

    def event_sort_key(event):
        parsed_date = event["event_date"]
        return (parsed_date is None, parsed_date or datetime.date.max, event["title"])

    all_events.sort(key=event_sort_key)

    dated_events = [event for event in all_events if event["event_date"]]
    undated_events = [event for event in all_events if not event["event_date"]]
    calendar_first_date = dated_events[0]["event_date"] if dated_events else today
    calendar_last_date = dated_events[-1]["event_date"] if dated_events else today
    calendar_start = calendar_first_date - datetime.timedelta(days=(calendar_first_date.weekday() + 1) % 7)
    calendar_end = calendar_last_date + datetime.timedelta(days=(6 - ((calendar_last_date.weekday() + 1) % 7)))
    calendar_events = {}
    for event in dated_events:
        recurring_match = re.search(
            r"Every\s+(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+Until\b",
            event["datetime_label"] or "",
            flags=re.IGNORECASE,
        )
        if recurring_match:
            weekday = [
                "monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"
            ].index(recurring_match.group(1).lower())
            occurrence = today + datetime.timedelta(days=(weekday - today.weekday()) % 7)
            while occurrence <= event["event_date"]:
                occurrence_event = dict(event)
                occurrence_event["event_date"] = occurrence
                calendar_events.setdefault(occurrence.isoformat(), []).append(occurrence_event)
                occurrence += datetime.timedelta(days=7)
        else:
            date_key = event["event_date"].isoformat()
            calendar_events.setdefault(date_key, []).append(event)
    calendar_days = (calendar_end - calendar_start).days + 1
    calendar_weeks = [
        [calendar_start + datetime.timedelta(days=day_offset) for day_offset in range(week * 7, week * 7 + 7)]
        for week in range(calendar_days // 7)
    ]
            
    EVENT_URLS = {
        "shea_theater": "https://sheatheater.org",
        "rendezvous": "https://thevoo.net",
        "tree_house": "https://treehousebrew.com/events-deerfield",
        "northampton_live": "https://northampton.live/calendar",
        "four_phantoms": "https://fourphantoms.com/lander",
        "franklin_chamber": "https://chamber.franklincc.org/events",
        "shelburne_falls": "https://www.shelburnefalls.com/calendar/",
        "visit_greenfield": "https://visitgreenfieldma.com/events/",
    }
    
    active_store_badges = [
        {
            "name": dataset.store_name,
            "range_label": format_date_range(dataset.flyer_start_date, dataset.flyer_end_date),
            "scraper_key": dataset.scraper_key,
            "flyer_url": EVENT_URLS.get(dataset.scraper_key, "#")
        }
        for dataset in active_datasets
    ]
    
    today_events = calendar_events.get(today.isoformat(), [])
    today_event_items = [
        {
            "id": ev["id"],
            "title": ev["title"],
            "store_name": ev["store_name"],
            "datetime_label": ev.get("datetime_label", ""),
            "description": ev.get("description", ""),
            "detail_url": ev.get("detail_url", ""),
            "is_movie": False,
        }
        for ev in today_events
    ]

    upcoming_movies = _get_upcoming_wheel_movies(db, today)
    wheel_items = _interleave_wheel_items(today_event_items, upcoming_movies)
    wheel_items_json = json.dumps(wheel_items, default=str)

    context = {
        "request": request,
        "has_data": bool(all_events),
        "all_events": all_events,
        "undated_events": undated_events,
        "store_events_map": store_events_map,
        "active_store_badges": active_store_badges,
        "calendar_first_date": calendar_first_date,
        "calendar_last_date": calendar_last_date,
        "calendar_weeks": calendar_weeks,
        "calendar_events": calendar_events,
        "today": today,
        "today_events": today_events,
        "wheel_items": wheel_items,
        "wheel_items_json": wheel_items_json,
        "today_events_json": json.dumps(today_event_items, default=str),
        "upcoming_movies_count": len(upcoming_movies),
    }
    return templates.TemplateResponse(request=request, name="events.html", context=context)


@app.get("/movies", response_class=HTMLResponse)
async def read_movies(request: Request, db: Session = Depends(get_db)):
    """Render current movie showtimes, formats, and theater info.

    Displays active film titles and showtimes for Greenfield Garden Cinemas
    and Cinemark at Hampshire Mall in Hadley, with filtering tabs and direct ticket links.
    """
    active_datasets = get_active_movie_datasets(db)
    try:
        import zoneinfo
        local_tz = zoneinfo.ZoneInfo("America/New_York")
        today = datetime.datetime.now(local_tz).date()
    except Exception:
        today = datetime.datetime.now(datetime.timezone.utc).date()

    all_movies = []
    theaters_map = {}

    THEATER_INFO = {
        "greenfield_garden_cinemas": {
            "name": "Greenfield Garden Cinemas",
            "tagline": "Independent Cinema in Downtown Greenfield",
            "address": "361 Main St, Greenfield, MA 01301",
            "phone": "(413) 774-4881",
            "url": "https://www.gardencinemas.net/",
            "badge_color": "bg-emerald-600",
            "badge_border": "border-emerald-500",
            "accent_text": "text-emerald-400",
        },
        "cinemark_hadley": {
            "name": "Cinemark at Hampshire Mall (Hadley)",
            "tagline": "XD Screens, Luxury Loungers & Full Amenities",
            "address": "367 Russell St, Hadley, MA 01035",
            "phone": "(413) 587-4237",
            "url": "https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
            "badge_color": "bg-red-600",
            "badge_border": "border-red-500",
            "accent_text": "text-red-400",
        },
    }

    for dataset in active_datasets:
        theaters_map[dataset.scraper_key] = []
        info = THEATER_INFO.get(dataset.scraper_key, {
            "name": dataset.store_name,
            "tagline": "Local Cinema",
            "address": "Franklin County / Pioneer Valley",
            "phone": "",
            "url": "#",
            "badge_color": "bg-indigo-600",
            "badge_border": "border-indigo-500",
            "accent_text": "text-indigo-400",
        })

        for deal in dataset.deals:
            desc = deal.description or ""
            poster_match = re.search(r"Poster:\s*(\S+)", desc)
            poster_url = poster_match.group(1) if poster_match else ""

            trailer_match = re.search(r"Trailer:\s*(\S+)", desc)
            trailer_url = trailer_match.group(1) if trailer_match else ""

            tickets_match = re.search(r"Tickets:\s*(\S+)", desc)
            tickets_url = tickets_match.group(1) if tickets_match else ""

            details_match = re.search(r"Details:\s*(\S+)", desc)
            details_url = details_match.group(1) if details_match else info["url"]

            dir_match = re.search(r"Director:\s*([^|]+)", desc)
            director = dir_match.group(1).strip() if dir_match else ""

            star_match = re.search(r"Starring:\s*([^|]+)", desc)
            starring = star_match.group(1).strip() if star_match else ""

            first_part = desc.split("|")[0].strip() if desc else ""
            rating_match = re.search(r"\b(G|PG-13|PG|R|NC-17|NR)\b", first_part)
            rating = rating_match.group(1) if rating_match else ""

            runtime_match = re.search(r"(\d+\s*hr(?:\s*\d+\s*min)?|\d+\s*min)", first_part, re.I)
            runtime = runtime_match.group(1) if runtime_match else ""

            formats_match = re.search(r"Formats?:\s*([^|]+)", desc)
            formats = formats_match.group(1).strip() if formats_match else ""

            times_raw = deal.sale_price or ""
            showtimes = [t.strip() for t in times_raw.split(",") if t.strip()]

            clean_desc = re.sub(r"\s*\|\s*(?:Poster|Trailer|Tickets|Details):.*", "", desc).strip()

            movie_item = {
                "id": deal.id,
                "theater_name": dataset.store_name,
                "scraper_key": dataset.scraper_key,
                "title": deal.item_name,
                "rating": rating,
                "runtime": runtime,
                "formats": formats,
                "showtimes": showtimes,
                "showtimes_raw": times_raw,
                "poster_url": poster_url,
                "trailer_url": trailer_url,
                "tickets_url": tickets_url or details_url,
                "details_url": details_url,
                "director": director,
                "starring": starring,
                "description": clean_desc,
                "theater_info": info,
            }
            all_movies.append(movie_item)
            theaters_map[dataset.scraper_key].append(movie_item)

    # Sort all movies by title
    all_movies.sort(key=lambda m: m["title"].lower())

    active_theater_badges = [
        {
            "scraper_key": ds.scraper_key,
            "name": ds.store_name,
            "count": len(theaters_map.get(ds.scraper_key, [])),
            "url": THEATER_INFO.get(ds.scraper_key, {}).get("url", "#"),
            "badge_color": THEATER_INFO.get(ds.scraper_key, {}).get("badge_color", "bg-indigo-600"),
        }
        for ds in active_datasets
    ]

    context = {
        "request": request,
        "has_data": bool(all_movies),
        "all_movies": all_movies,
        "theaters_map": theaters_map,
        "theater_info": THEATER_INFO,
        "active_theater_badges": active_theater_badges,
        "today": today,
    }
    return templates.TemplateResponse(request=request, name="movies.html", context=context)


async def _get_pharmacy_analysis(db: Session, active_datasets: List[StoreDataset], all_deals: List[Dict]) -> Dict:
    """Load or compute AI scoring and department categorization for pharmacy deals."""
    if not all_deals:
        return {
            "scored_deals": [],
            "top_overall": [],
            "deals_by_category": {c: [] for c in PHARMACY_CATEGORIES},
            "best_pharmacy": None,
        }

    sig = ":".join(
        f"{ds.id}_{ds.finished_at.isoformat() if ds.finished_at else ''}_{len(ds.deals)}"
        for ds in sorted(active_datasets, key=lambda d: d.id)
    )

    cached_config = db.query(Configuration).filter(Configuration.key == "pharmacy_ai_analysis").first()
    if cached_config and cached_config.value:
        try:
            payload = json.loads(cached_config.value)
            if payload.get("sig") == sig and payload.get("analysis"):
                return payload["analysis"]
        except Exception as e:
            logger.warning(f"Failed to parse cached pharmacy analysis: {e}")

    analyzer = GeminiAnalyzer()
    analysis = await analyzer.analyze_pharmacy_deals(all_deals)

    try:
        if not cached_config:
            cached_config = Configuration(key="pharmacy_ai_analysis", value=json.dumps({"sig": sig, "analysis": analysis}))
            db.add(cached_config)
        else:
            cached_config.value = json.dumps({"sig": sig, "analysis": analysis})
        db.commit()
    except Exception as e:
        logger.warning(f"Could not persist pharmacy analysis cache: {e}")
        db.rollback()

    return analysis


@app.get("/pharmacies", response_class=HTMLResponse)
async def read_pharmacies(request: Request, db: Session = Depends(get_db)):
    """Render weekly circular promotions for local pharmacies in Greenfield and Turners Falls.

    Displays AI-scored deals, category departments, top picks overall, and store-by-store
    comparisons for CVS Pharmacy and Walgreens across Greenfield and Turners Falls.
    """
    active_datasets = get_active_pharmacy_datasets(db)

    PHARMACY_INFO = {
        "cvs_greenfield": {
            "name": "CVS Pharmacy",
            "town": "Greenfield",
            "tagline": "24-Hour Pharmacy & Health Hub",
            "address": "137 Federal St, Greenfield, MA 01301",
            "phone": "(413) 774-7201",
            "hours": "Open 24 Hours",
            "url": "https://www.cvs.com/store-locator/cvs-pharmacy-address/137+FEDERAL+STREET+GREENFIELD+MA+01301-4404/storeid/01094",
            "circular_url": "https://www.cvs.com/weeklyad",
            "badge_color": "bg-red-600",
            "badge_border": "border-red-500",
            "accent_text": "text-red-400",
        },
        "walgreens_greenfield": {
            "name": "Walgreens",
            "town": "Greenfield",
            "tagline": "Full-Service Pharmacy & Essentials",
            "address": "5 Pierce St, Greenfield, MA 01301",
            "phone": "(413) 773-3801",
            "hours": "Mon–Sun 8:00 AM – 10:00 PM",
            "url": "https://www.walgreens.com/locator/walgreens-5+pierce+st-greenfield-ma-01301/id=10672",
            "circular_url": "https://www.walgreens.com/offers/offers.jsp",
            "badge_color": "bg-sky-600",
            "badge_border": "border-sky-500",
            "accent_text": "text-sky-400",
        },
        "walgreens_turners_falls": {
            "name": "Walgreens",
            "town": "Turners Falls",
            "tagline": "Community Pharmacy & Convenience",
            "address": "240 Avenue A, Turners Falls, MA 01376",
            "phone": "(413) 863-3107",
            "hours": "Mon–Fri 8am–8pm, Sat 9–6, Sun 10–6",
            "url": "https://www.walgreens.com/locator/walgreens-240+avenue+a-turners+falls-ma-01376/id=17960",
            "circular_url": "https://www.walgreens.com/offers/offers.jsp",
            "badge_color": "bg-indigo-600",
            "badge_border": "border-indigo-500",
            "accent_text": "text-indigo-400",
        },
    }

    raw_deals = []
    for dataset in active_datasets:
        info = PHARMACY_INFO.get(dataset.scraper_key, {
            "name": dataset.store_name,
            "town": "Franklin County",
            "tagline": "Local Pharmacy",
            "address": "",
            "phone": "",
            "hours": "",
            "url": "#",
            "circular_url": "#",
            "badge_color": "bg-teal-600",
            "badge_border": "border-teal-500",
            "accent_text": "text-teal-400",
        })

        for deal in dataset.deals:
            desc = deal.description or ""
            img_match = re.search(r"Image:\s*(\S+)", desc)
            image_url = img_match.group(1) if img_match else ""
            clean_desc = re.sub(r"\s*\|\s*Image:\s*\S+", "", desc).strip()

            deal_item = {
                "id": deal.id,
                "store_name": dataset.store_name,
                "scraper_key": dataset.scraper_key,
                "town": info["town"],
                "name": deal.item_name,
                "price": deal.sale_price,
                "description": clean_desc,
                "image_url": image_url,
                "store_info": info,
                "flyer_start": str(dataset.flyer_start_date) if dataset.flyer_start_date else "",
                "flyer_end": str(dataset.flyer_end_date) if dataset.flyer_end_date else "",
            }
            raw_deals.append(deal_item)

    analysis = await _get_pharmacy_analysis(db, active_datasets, raw_deals)

    scored_deals = analysis.get("scored_deals", [])
    top_overall = analysis.get("top_overall", [])
    deals_by_category = analysis.get("deals_by_category", {})
    best_pharmacy = analysis.get("best_pharmacy")

    stores_map = {ds.scraper_key: [] for ds in active_datasets}
    for d in scored_deals:
        key = d.get("scraper_key")
        if key in stores_map:
            stores_map[key].append(d)

    active_store_badges = [
        {
            "scraper_key": ds.scraper_key,
            "name": ds.store_name,
            "count": len(stores_map.get(ds.scraper_key, [])),
            "town": PHARMACY_INFO.get(ds.scraper_key, {}).get("town", ""),
            "url": PHARMACY_INFO.get(ds.scraper_key, {}).get("url", "#"),
            "circular_url": PHARMACY_INFO.get(ds.scraper_key, {}).get("circular_url", "#"),
            "badge_color": PHARMACY_INFO.get(ds.scraper_key, {}).get("badge_color", "bg-teal-600"),
            "flyer_start": ds.flyer_start_date,
            "flyer_end": ds.flyer_end_date,
        }
        for ds in active_datasets
    ]

    context = {
        "request": request,
        "has_data": bool(scored_deals),
        "top_overall": top_overall,
        "deals_by_category": deals_by_category,
        "best_pharmacy": best_pharmacy,
        "all_deals": scored_deals,
        "stores_map": stores_map,
        "pharmacy_info": PHARMACY_INFO,
        "active_store_badges": active_store_badges,
        "categories": PHARMACY_CATEGORIES,
        "total_deals_count": len(scored_deals),
    }
    return templates.TemplateResponse(request=request, name="pharmacies.html", context=context)


@app.get("/admin/login", response_class=HTMLResponse)

async def admin_login_page(request: Request):
    if _is_admin_authenticated(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"request": request, "error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    password = form.get("password")
    stored_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
    if not stored_pass or password != stored_pass.value:
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"request": request, "error": "Invalid password"},
        )

    request.session["admin_authenticated"] = True
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="admin.html", context=_build_admin_context(request, db))


@app.post("/admin/run/full", response_class=HTMLResponse)
async def admin_run_full(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect

    background_tasks.add_task(run_full_scrape, trigger_mode="manual_full")
    context = _build_admin_context(request, db, message="Full run queued in the background.")
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/admin/run/groceries", response_class=HTMLResponse)
async def admin_run_groceries(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect

    background_tasks.add_task(run_grocery_scrape, trigger_mode="manual_grocery")
    context = _build_admin_context(request, db, message="All groceries run queued in the background.")
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/admin/run/{scraper_key}", response_class=HTMLResponse)
async def admin_run_single(scraper_key: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect

    valid_scraper_keys = {
        entry["scraper_key"]
        for entry in ScraperManager().list_scrapers()
        if entry["scraper_key"] not in ("full_run", "grocery_run")
    }
    if scraper_key not in valid_scraper_keys:
        context = _build_admin_context(request, db, error=f"Unknown scraper '{scraper_key}'.")
        return templates.TemplateResponse(request=request, name="admin.html", context=context, status_code=404)

    background_tasks.add_task(run_single_scrape, scraper_key=scraper_key, trigger_mode="manual_single")
    context = _build_admin_context(request, db, message=f"{scraper_key} queued in the background.")
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/admin/change-password", response_class=HTMLResponse)
async def admin_change_password(request: Request, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect

    form = await request.form()
    current_password = form.get("current_password")
    new_password = form.get("new_password")

    stored_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
    if not stored_pass:
        context = _build_admin_context(request, db, error="Configuration error")
        return templates.TemplateResponse(request=request, name="admin.html", context=context)
    if current_password != stored_pass.value:
        context = _build_admin_context(request, db, error="Invalid current password")
        return templates.TemplateResponse(request=request, name="admin.html", context=context)

    stored_pass.value = new_password
    db.commit()
    context = _build_admin_context(request, db, message="Password updated successfully.")
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/api/refresh")
async def trigger_refresh(request: Request, background_tasks: BackgroundTasks):
    if not _is_admin_authenticated(request):
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    logger.info("Manual refresh triggered from API.")
    background_tasks.add_task(run_full_scrape, trigger_mode="manual_full")
    return {"message": "Full run started in the background."}
