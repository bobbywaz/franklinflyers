from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import get_db, init_db
from .models import Run, Deal, BestStore, FailedScrape, GasPrice
from .scheduler import start_scheduler, run_scrape_and_analyze
import logging
import json

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
    latest_run = db.query(Run).filter(Run.is_ready == True).order_by(Run.run_date.desc()).first()
    
    context = {
        "request": request,
        "has_data": latest_run is not None,
        "latest_run": latest_run,
        "failed_scrapes": [],
        "best_store": None,
        "top_overall": [],
        "deals_by_category": {},
        "seasonal_guide": None,
        "recipe_idea": None,
        "gas_by_city": {}
    }

    if latest_run:
        context["failed_scrapes"] = latest_run.failed_scrapes
        context["best_store"] = latest_run.best_store
        
        # Group gas prices by city
        gas_by_city = {}
        for gp in latest_run.gas_prices:
            if gp.city not in gas_by_city:
                gas_by_city[gp.city] = []
            gas_by_city[gp.city].append(gp)
        context["gas_by_city"] = gas_by_city
        
        if latest_run.seasonal_info:
            try:
                context["seasonal_guide"] = json.loads(latest_run.seasonal_info)
            except:
                pass

        if latest_run.recipe_idea:
            try:
                context["recipe_idea"] = json.loads(latest_run.recipe_idea)
            except:
                pass
        
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

@app.post("/api/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks, pin: str = None):
    if pin != "8156":
        logger.warning(f"Unauthorized refresh attempt with PIN: {pin}")
        return JSONResponse(status_code=401, content={"message": "Unauthorized: Invalid PIN."})
    
    logger.info("Manual refresh triggered with valid PIN.")
    background_tasks.add_task(run_scrape_and_analyze)
    return {"message": "Scrape process started in the background."}
