import json
import logging
import os
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .database import SessionLocal, get_db, init_db
from .manager import ScraperManager
from .models import Configuration, Run, StoreDataset
from .scheduler import run_full_scrape, run_single_scrape, start_scheduler
from .store_utils import (
    STATUS_SUCCESS,
    format_date_range,
    get_active_dataset_by_key,
    get_active_grocery_datasets,
    get_latest_active_gas_dataset,
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
    active_gas_dataset = get_latest_active_gas_dataset(db)
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

    gas_by_city = {}
    if active_gas_dataset:
        for gas_price in active_gas_dataset.gas_prices:
            gas_by_city.setdefault(gas_price.city, []).append(gas_price)

    return {
        "request": request,
        "has_data": bool(top_overall or deals_by_category or active_store_badges or gas_by_city),
        "latest_run": latest_run,
        "best_store": best_store,
        "top_overall": top_overall,
        "deals_by_category": deals_by_category,
        "seasonal_guide": seasonal_guide,
        "recipe_idea": recipe_idea,
        "gas_by_city": gas_by_city,
        "active_store_badges": active_store_badges,
    }


def _build_admin_context(request: Request, db: Session, message: str = None, error: str = None):
    manager = ScraperManager()
    latest_run = db.query(Run).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()
    cards = []
    latest_published_datasets = [entry.dataset for entry in latest_run.published_stores if entry.dataset] if latest_run else []

    for entry in manager.list_scrapers():
        scraper_key = entry["scraper_key"]
        if scraper_key == "full_run":
            cards.append(
                {
                    "scraper_key": "full_run",
                    "name": "Full Run",
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
        active_dataset = (
            get_latest_active_gas_dataset(db)
            if scraper_key == "gas"
            else get_active_dataset_by_key(db, scraper_key)
        )

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
        if active_dataset and active_dataset.kind == "grocery":
            date_label = format_date_range(active_dataset.flyer_start_date, active_dataset.flyer_end_date)
        elif active_dataset and active_dataset.kind == "gas" and active_dataset.expires_at:
            date_label = f"Fresh until {active_dataset.expires_at.strftime('%Y-%m-%d %H:%M UTC')}"
        elif latest_success and latest_success.kind == "grocery":
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
    context = _build_admin_context(request, db, message="Full run started in the background.")
    return templates.TemplateResponse(request=request, name="admin.html", context=context)


@app.post("/admin/run/{scraper_key}", response_class=HTMLResponse)
async def admin_run_single(scraper_key: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    redirect = _require_admin(request)
    if redirect:
        return redirect

    valid_scraper_keys = {entry["scraper_key"] for entry in ScraperManager().list_scrapers() if entry["scraper_key"] != "full_run"}
    if scraper_key not in valid_scraper_keys:
        context = _build_admin_context(request, db, error=f"Unknown scraper '{scraper_key}'.")
        return templates.TemplateResponse(request=request, name="admin.html", context=context, status_code=404)

    background_tasks.add_task(run_single_scrape, scraper_key=scraper_key, trigger_mode="manual_single")
    context = _build_admin_context(request, db, message=f"{scraper_key} started in the background.")
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
