import asyncio
import logging
from app.scheduler import run_full_scrape

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting full scrape manually")
    await run_full_scrape('manual_full')
    logger.info("Finished full scrape manually")

if __name__ == "__main__":
    asyncio.run(main())
