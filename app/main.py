from fastapi import FastAPI, Depends, Request, BackgroundTasks, Security, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from .database import get_db, init_db
from .models import Run, Deal, BestStore, FailedScrape
from .scheduler import start_scheduler, run_scrape_and_analyze
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Franklin Flyers")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    init_db()
    app.state.scheduler = start_scheduler()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    latest_run = db.query(Run).order_by(Run.run_date.desc()).first()
    
    context = {
        "request": request,
        "has_data": latest_run is not None,
        "latest_run": latest_run,
        "failed_scrapes": [],
        "best_store": None,
        "top_overall": [],
        "deals_by_category": {}
    }

    if latest_run:
        context["failed_scrapes"] = latest_run.failed_scrapes
        context["best_store"] = latest_run.best_store
        
        # Top 6 deals overall
        context["top_overall"] = db.query(Deal).filter(Deal.run_id == latest_run.id).order_by(Deal.score.desc()).limit(6).all()
        
        # Deals by category
        deals = db.query(Deal).filter(Deal.run_id == latest_run.id).all()
        by_cat = {}
        for d in deals:
            if d.category not in by_cat:
                by_cat[d.category] = []
            by_cat[d.category].append(d)
        context["deals_by_category"] = by_cat

    return templates.TemplateResponse(request=request, name="index.html", context=context)

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    admin_api_key = os.getenv("ADMIN_API_KEY")
    if not admin_api_key:
        logger.error("ADMIN_API_KEY not set in environment variables.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key not configured."
        )
    if api_key_header == admin_api_key:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )

@app.post("/api/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks, api_key: str = Security(get_api_key)):
    logger.info("Manual refresh triggered.")
    background_tasks.add_task(run_scrape_and_analyze)
    return {"message": "Scrape process started in the background."}
