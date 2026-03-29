import asyncio
import json
import os
import sys

# Add project root to path for imports
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Run, Deal
from app.gemini_analyzer import GeminiAnalyzer
from dotenv import load_dotenv

load_dotenv()

async def regen_recipe():
    print("Regenerating recipe for latest run...")
    db = SessionLocal()
    try:
        latest_run = db.query(Run).order_by(Run.run_date.desc()).first()
        if not latest_run:
            print("No runs found in database.")
            return

        deals = db.query(Deal).filter(Deal.run_id == latest_run.id).order_by(Deal.score.desc()).all()
        if not deals:
            print("No deals found for latest run.")
            return

        # Prepare deals for analyzer
        deals_data = [
            {"item_name": d.item_name, "sale_price": d.sale_price, "category": d.category}
            for d in deals
        ]

        analyzer = GeminiAnalyzer()
        recipe = await analyzer.generate_recipe(deals_data)
        
        if recipe:
            latest_run.recipe_idea = json.dumps(recipe)
            db.commit()
            print(f"Successfully regenerated recipe: {recipe.get('recipe_name')}")
        else:
            print("Failed to generate recipe.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(regen_recipe())
