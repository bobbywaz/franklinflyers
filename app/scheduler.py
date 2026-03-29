from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
import json
from .manager import ScraperManager
from .gemini_analyzer import GeminiAnalyzer
from .database import SessionLocal, init_db
from .models import Run, Deal, BestStore, FailedScrape, GasPrice

logger = logging.getLogger(__name__)

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
        
        run_date_str = new_run.run_date.strftime('%Y-%m-%d %H:%M')

        all_deals, gas_prices, failed_scrapes = await manager.run_all_scrapers(run_date=run_date_str)
        
        for fail in failed_scrapes:
            db.add(FailedScrape(
                run_id=new_run.id,
                store_name=fail['store_name'],
                error_message=fail['error_message']
            ))

        # Save gas prices
        for gp in gas_prices:
            db.add(GasPrice(
                run_id=new_run.id,
                station_name=gp['station_name'],
                address=gp['address'],
                city=gp['city'],
                price=gp['price'],
                fuel_type=gp['fuel_type'],
                updated_at=gp['updated_at']
            ))

        if all_deals:
            analysis = await analyzer.analyze_deals(all_deals)
            
            # Save seasonal info
            if analysis.get('seasonal_guide'):
                logger.info(f"Saving seasonal_info for run: {analysis['seasonal_guide']}")
                new_run.seasonal_info = json.dumps(analysis['seasonal_guide'])
            else:
                logger.warning("No seasonal_guide found in analysis results.")

            # Save recipe idea
            if analysis.get('recipe_idea'):
                logger.info(f"Saving recipe_idea for run: {analysis['recipe_idea']}")
                new_run.recipe_idea = json.dumps(analysis['recipe_idea'])
            else:
                logger.warning("No recipe_idea found in analysis results.")

            # Save best store
            if analysis.get('best_store'):
                bs = analysis['best_store']
                
                # Ensure strengths/weaknesses are strings for SQLite
                strengths = bs.get('strengths', '')
                if isinstance(strengths, list):
                    strengths = "\n".join(strengths)
                
                weaknesses = bs.get('weaknesses', '')
                if isinstance(weaknesses, list):
                    weaknesses = "\n".join(weaknesses)

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
            
        db.commit()
        logger.info(f"Successfully finished scrape run {new_run.id}.")
            
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
