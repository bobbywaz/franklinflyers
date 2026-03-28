# Franklin Flyers

Franklin Flyers is a Dockerized web application that automatically scrapes weekly grocery flyers for the Greenfield / Turners Falls area in Massachusetts. It uses the Gemini API to evaluate and score items, identifying genuine deals based on value and recent regional pricing trends.

## Features
- **Automated Scheduling:** Scrapes flyers automatically using background jobs (default: Mon & Thu at 2:00 AM).
- **AI-Powered Evaluation:** Uses Gemini 2.5 Flash to categorize items, detect fake sales, and score true value out of 10.
- **"Best Store" Recommendation:** Identifies the overall best store to shop at for the week.
- **Resilient Scraping:** Uses headless Chromium via Playwright to parse JS-heavy flyer pages.

## Requirements
- Docker & Docker Compose
- A valid Google Gemini API Key

## Setup Instructions

1. **Configure Environment:**
   Copy the example environment file and insert your API key.
   ```bash
   cp .env.example .env
   ```
   Open `.env` and replace `your_gemini_api_key_here` with your actual Gemini API key. You can also adjust the cron schedule variables if desired.

2. **Build and Run:**
   Bring up the Docker container. This will build the Python environment, download Chromium for Playwright, and start the FastAPI web server.
   ```bash
   docker-compose up -d --build
   ```

3. **Access the Web App:**
   Open your browser and navigate to:
   http://localhost:8000

## Manual Trigger / Refresh
To trigger an immediate flyer scrape:
- **From the UI:** Click the "Refresh Now" button on the webpage.
- **From CLI:** You can manually ping the endpoint:
  ```bash
  curl -X POST http://localhost:8000/api/refresh
  ```
*Note: The scrape takes several minutes as it launches a headless browser, waits for DOMs to load, and queries the Gemini API.*

## Troubleshooting
- **No Deals Showing:** If a store changes its flyer viewer layout (e.g., switches to a different embedded PDF/JS vendor), the scraper may fail. Check the "Failed Scrapes" section in the UI. 
- **Fixing Scrapers:** You will need to inspect the live website DOM and update the CSS selectors in the corresponding `app/scraper/adapters/*.py` file.
- **Viewing Logs:**
  ```bash
  docker-compose logs -f web
  ```

## Adding More Stores
To add a new store, create a new class inheriting from `BaseScraper` in `/app/scraper/adapters/`. Then, register your new scraper in `app/scraper/manager.py` by adding it to the `SCRAPERS` list.