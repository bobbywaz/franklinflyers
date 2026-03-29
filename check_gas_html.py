import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://dmv-test-pro.com/gas-prices/massachusetts/greenfield', wait_until='domcontentloaded')
        await page.wait_for_selector('.gas-tab-item')
        item = await page.query_selector('.gas-tab-item')
        print(await item.inner_html())
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
