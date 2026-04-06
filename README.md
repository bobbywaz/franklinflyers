# Franklin Flyers

Franklin Flyers is a Dockerized web application that automatically scrapes weekly grocery flyers for the Greenfield / Turners Falls area in Massachusetts. It uses the Gemini API to evaluate and score items, identifying genuine deals based on value and recent regional pricing trends.

## Features
- **Automated Scheduling:** Scrapes flyers automatically using background jobs (default: Mon & Thu at 2:00 AM).
- **Vision-Powered Extraction:** Uses Gemini 2.5 Flash to "see" and extract deals from complex flyer PDFs and JS-heavy circulars, ensuring high accuracy and verification of store location and dates.
- **AI-Powered Evaluation:** Uses Gemini to categorize items, detect fake sales, and score true value out of 10.
- **"Best Store" Recommendation:** Identifies the overall best store to shop at for the week.
- **Admin Dashboard:** Secure interface for manual refreshes and password management.

## Setup Instructions

1. **Configure Environment:**
   Copy the example environment file and insert your API key.
   ```bash
   cp .env.example .env
   ```
   Open `.env` and replace `your_gemini_api_key_here` with your actual Gemini API key.

2. **Build and Run:**
   Bring up the Docker containers.
   ```bash
   docker-compose up -d --build
   ```

3. **Access the Web App:**
   Open your browser and navigate to:
   http://localhost:8000

## Admin Dashboard
Access the admin dashboard at `http://localhost:8000/admin`.
- **Default Password:** `changeme`
- **Features:** 
  - Trigger immediate data refresh (scrapes all stores and gas prices).
  - Update admin password.

## Manual Trigger / Refresh
To trigger an immediate flyer scrape:
- **From Admin UI:** Go to `/admin`, enter your password, and click "Update Prices Now".
- **From CLI:** You can manually ping the endpoint:
  ```bash
  curl -X POST http://localhost:8000/api/refresh?pin=your_admin_password
  ```
*Note: The scrape takes several minutes as it launches a headless browser, waits for content to load, and queries the Gemini API.*

## Troubleshooting
- **No Deals Showing:** If a store changes its flyer viewer layout, the scraper may fail. Check the "Failed Scrapes" section in the UI. 
- **Viewing Logs:**
  ```bash
  docker-compose logs -f web
  ```

## Adding More Stores
To add a new store, create a new class inheriting from `BaseScraper` in `app/scrapers/`. Then, register your new scraper in `app/manager.py` by adding it to the `self.scrapers` list.
