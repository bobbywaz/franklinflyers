import asyncio
from playwright.async_api import async_playwright
import re

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Using Greenfield as the test case
        url = 'https://dmv-test-pro.com/gas-prices/massachusetts/greenfield'
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_selector('.gas-tab-item')
        
        items = await page.query_selector_all('.gas-tab-item')
        for i, item in enumerate(items[:3]):
            name_el = await item.query_selector(".tab-item-title")
            name = await name_el.inner_text() if name_el else "Unknown"
            
            html = await item.inner_html()
            print(f"\n--- Station: {name} ---")
            
            # Check for standard text first
            text = await item.inner_text()
            clean_text = text.replace("\n", " | ")
            print(f"Visible Text: {clean_text}")
            
            # Look for visible time element
            time_el = await item.query_selector(".tab-item-time")
            if time_el:
                print(f"Found Visible Time Element: {await time_el.inner_text()}")

            # Look for the commented out time specifically
            match = re.search(r'<!--\s*<div class="tab-item-time">(.*?)</div>\s*-->', html)
            if match:
                print(f"Found Commented Time: {match.group(1)}")
            else:
                # Search for any string that looks like an update time in the HTML
                time_match = re.search(r'(\d+\s+(DAY|HOUR|MINUTE|WEEK|MONTH)S?\s+AGO)', html, re.IGNORECASE)
                if time_match:
                    print(f"Found potential time string in HTML: {time_match.group(1)}")
                else:
                    print("No update time found in HTML or comments.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
