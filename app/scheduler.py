from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
import json
from .manager import ScraperManager
from .gemini_analyzer import GeminiAnalyzer
from .database import SessionLocal, init_db
from .models import Run, Deal, BestStore, FailedScrape, GasPrice

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Default to INFO, but manager/scrapers will log details

async def run_scrape_and_analyze():
    logger.info("--- STARTING SCHEDULED SCRAPE JOB ---")
    manager = ScraperManager()
    analyzer = GeminiAnalyzer()
    
    db = SessionLocal()
    try:
        new_run = Run()
        db.add(new_run)
        db.commit()
        db.refresh(new_run)
        logger.info(f"Initialized new database run. ID: {new_run.id}")
        
        run_date_str = new_run.run_date.strftime('%Y-%m-%d %H:%M')

        logger.info("Executing scrapers (this may take 1-2 minutes)...")
        all_deals, gas_prices, failed_scrapes = await manager.run_all_scrapers(run_date=run_date_str)
        
        logger.info(f"Scrape results: {len(all_deals)} grocery deals, {len(gas_prices)} gas prices.")
        
        if failed_scrapes:
            logger.warning(f"{len(failed_scrapes)} scrapers failed: {[f['store_name'] for f in failed_scrapes]}")
            for fail in failed_scrapes:
                db.add(FailedScrape(
                    run_id=new_run.id,
                    store_name=fail['store_name'],
                    error_message=fail['error_message']
                ))

        # Save gas prices
        logger.info("Saving gas prices to database...")
        for gp in gas_prices:
            db.add(GasPrice(
                run_id=new_run.id,
                station_name=gp['station_name'],
                address=gp['address'],
                city=gp['city'],
                price=gp['price'],
                fuel_type=gp['fuel_type'],
                updated_at=gp['updated_at'],
                source_updated_at=gp['source_updated_at']
            ))

        if all_deals:
            logger.info("Starting Gemini AI analysis of grocery deals...")
            analysis = await analyzer.analyze_deals(all_deals)
            
            # Save seasonal info
            if analysis.get('seasonal_guide'):
                new_run.seasonal_info = json.dumps(analysis['seasonal_guide'])

            # Save recipe idea
            if analysis.get('recipe_idea'):
                new_run.recipe_idea = json.dumps(analysis['recipe_idea'])

            # Save best store
            if analysis.get('best_store'):
                bs = analysis['best_store']
                strengths = bs.get('strengths', '')
                if isinstance(strengths, list): strengths = "\n".join(strengths)
                weaknesses = bs.get('weaknesses', '')
                if isinstance(weaknesses, list): weaknesses = "\n".join(weaknesses)

                db.add(BestStore(
                    run_id=new_run.id,
                    store_name=bs['store_name'],
                    summary=bs['summary'],
                    strengths=strengths,
                    weaknesses=weaknesses,
                    score=bs['score']
                ))

            # Save scored deals
            for d in analysis.get('scored_deals', []):
                db.add(Deal(
                    run_id=new_run.id,
                    store_name=d['store_name'],
                    item_name=d['item_name'],
                    description=d.get('size', ''),
                    sale_price=d['sale_price'],
                    category=d['category'],
                    score=d['score'],
                    explanation=d['explanation']
                ))
        else:
            logger.warning("No grocery deals were found to analyze.")
            
        new_run.is_ready = True
        db.commit()
        logger.info(f"--- SCRAPE RUN {new_run.id} FINISHED SUCCESSFULLY ---")
            
    except Exception as e:
        logger.error(f"FATAL ERROR in scheduled job: {e}", exc_info=True)
    finally:
        db.close()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    cron_expr = os.getenv("SCRAPE_SCHEDULE", "0 2 * * 1,4")
    scheduler.add_job(run_scrape_and_analyze, CronTrigger.from_crontab(cron_expr))
    scheduler.start()
    logger.info(f"Scheduler started with cron: {cron_expr}")
    return scheduler
