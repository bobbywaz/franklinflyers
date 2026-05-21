import asyncio
import logging
import json
from playwright.async_api import async_playwright
from app.scrapers.stop_and_shop import StopAndShopScraper

logging.basicConfig(level=logging.INFO)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        scraper = StopAndShopScraper()
        result = await scraper.scrape(page)
        if result and "payload" in result:
            print(f"Scraped {result['payload'].get('items_scraped')} items if successful")
            deals = result['payload'].get('deals', [])
            print(f"First 3 deals: {deals[:3]}")
        else:
            print(f"Result: {result}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
