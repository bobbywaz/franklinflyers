import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://flipp.com/en-us/greenfield-ma/flyer/7904219", wait_until="networkidle")
        print("Title:", await page.title())
        overlays = await page.locator("button.item-overlay").count()
        print("Overlays:", overlays)
        if overlays == 0:
            print(await page.content())
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
