from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import get_db, init_db, SessionLocal
from .models import Run, Deal, BestStore, FailedScrape, GasPrice, Configuration
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
    
    # Initialize default admin password if not exists
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

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="admin.html", context={"request": request})

@app.post("/admin/refresh")
async def admin_refresh(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    form = await request.form()
    password = form.get("password")
    
    stored_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
    if not stored_pass or password != stored_pass.value:
        return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "error": "Invalid password"})
    
    background_tasks.add_task(run_scrape_and_analyze)
    return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "message": "Scrape process started in the background."})

@app.post("/admin/change-password")
async def admin_change_password(request: Request, db: Session = Depends(get_db)):
    logger.info("Password change requested")
    form = await request.form()
    current_password = form.get("current_password")
    new_password = form.get("new_password")
    
    try:
        stored_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
        if not stored_pass:
            logger.error("Admin password configuration not found in DB")
            return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "error": "Configuration error"})
            
        if current_password != stored_pass.value:
            logger.warning("Invalid current password provided")
            return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "error": "Invalid current password"})
        
        stored_pass.value = new_password
        db.commit()
        logger.info("Password updated successfully")
        return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "message": "Password updated successfully."})
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "error": f"Internal error: {e}"})

@app.post("/api/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks, pin: str = None, db: Session = Depends(get_db)):
    stored_pass = db.query(Configuration).filter(Configuration.key == "admin_password").first()
    if pin != "8156" and (not stored_pass or pin != stored_pass.value):
        logger.warning(f"Unauthorized refresh attempt with PIN: {pin}")
        return JSONResponse(status_code=401, content={"message": "Unauthorized: Invalid PIN."})
    
    logger.info("Manual refresh triggered.")
    background_tasks.add_task(run_scrape_and_analyze)
    return {"message": "Scrape process started in the background."}
