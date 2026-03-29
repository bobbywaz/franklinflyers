from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
from .manager import ScraperManager
from .gemini_analyzer import GeminiAnalyzer
from .database import SessionLocal, init_db
from .models import Run, Deal, BestStore, FailedScrape

logger = logging.getLogger(__name__)

def _format_list_to_string(value):
    if isinstance(value, list):
        return "\n".join(value)
    return value

async def run_scrape_and_analyze():
    logger.info("Starting scheduled scrape job...")
    manager = ScraperManager()
    analyzer = GeminiAnalyzer()
    
    db = SessionLocal()
    try:
        new_run = Run()
        db.add(new_run)
        db.commit()
        db.refresh(new_run)

        all_deals, failed_scrapes = await manager.run_all_scrapers()
        
        for fail in failed_scrapes:
            db.add(FailedScrape(
                run_id=new_run.id,
                store_name=fail['store_name'],
                error_message=fail['error_message']
            ))

        if all_deals:
            analysis = await analyzer.analyze_deals(all_deals)
            
            # Save best store
            if analysis.get('best_store'):
                bs = analysis['best_store']
                
                # Ensure strengths/weaknesses are strings for SQLite
                strengths = _format_list_to_string(bs.get('strengths', ''))
                weaknesses = _format_list_to_string(bs.get('weaknesses', ''))

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
                    sale_price=d['sale_price'],
                    category=d['category'],
                    score=d['score'],
                    explanation=d['explanation']
                ))
            
            logger.info(f"Successfully finished scrape run {new_run.id}.")
        else:
            logger.warning("No deals found during scrape run.")
            
        db.commit()

    except Exception as e:
        logger.error(f"Error in scheduled job: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Defaults to Monday and Thursday at 2 AM
    cron_expr = os.getenv("SCRAPE_SCHEDULE", "0 2 * * 1,4")
    
    scheduler.add_job(
        run_scrape_and_analyze,
        CronTrigger.from_crontab(cron_expr)
    )
    
    scheduler.start()
    logger.info(f"Scheduler started with cron: {cron_expr}")
    return scheduler
