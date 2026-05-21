import asyncio
import logging
import json
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from app.scrapers.stop_and_shop import StopAndShopScraper

# Set up logging to see the internal scraper diagnostics
logging.basicConfig(level=logging.INFO)

async def test_scraper():
    scraper = StopAndShopScraper()
    
    print("--- Testing Stop & Shop API Path ---")
    items = await scraper._fetch_flipp_api_items()
    if items:
        print(f"✅ API Success: Found {len(items)} items matching Stop & Shop.")
        payload = scraper._build_flipp_api_payload(items)
        print(f"Deals extracted: {len(payload['deals'])}")
        if payload['deals']:
            print(f"Sample Deal: {payload['deals'][0]}")
    else:
        print("❌ API Path returned no items (or failed).")
        
    print("\n--- Testing Stop & Shop Browser Fallback (Headless) ---")
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # Manually trigger the fallback method
            print("Starting browser extraction (this takes ~30-60 seconds due to anti-bot delays)...")
            result = await scraper._scrape_flipp_overlay(page)
            if result:
                print(f"✅ Browser Success: Found {len(result.get('deals', []))} deals.")
            else:
                print("❌ Browser Fallback failed.")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scraper())