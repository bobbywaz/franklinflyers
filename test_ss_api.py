import asyncio
import httpx
import datetime

async def main():
    url = "https://backflipp.wishabi.com/flipp/items/search?locale=en-us&postal_code=01376&q=Stop%20And%20Shop"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    items = data.get("items", [])
    print(f"Got {len(items)} items")
    if items:
        valid_from = items[0].get("valid_from")
        print(f"valid_from: {valid_from}")
        print(f"Parsed: {datetime.datetime.fromisoformat(valid_from).date()}")
        print(f"Sample item: {items[0]['name']} - {items[0].get('current_price')} - {items[0].get('sale_story')}")

if __name__ == "__main__":
    asyncio.run(main())
