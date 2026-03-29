import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"Navigating to ALDI...")
        await page.goto("https://www.aldi.us/weekly-specials/our-weekly-ads/", timeout=60000)
        await asyncio.sleep(5)
        title = await page.title()
        print(f"Page Title: {title}")
        
        # Look for elements that might contain deals
        # Many flyers use iframes or complex JS widgets (like Flipp)
        iframes = page.frames
        print(f"Found {len(iframes)} frames.")
        for i, frame in enumerate(iframes):
            print(f"Frame {i}: {frame.url}")
            
        # Try to find common "item" or "deal" classes
        # This is a shot in the dark without seeing the DOM
        
        # Save a screenshot to see what's happening
        await page.screenshot(path="aldi_screenshot.png")
        print("Saved screenshot to aldi_screenshot.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
