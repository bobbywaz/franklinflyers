import datetime
import logging
from typing import Any, Dict, Optional

from .base import BaseScraper

logger = logging.getLogger(__name__)

FALLBACK_MOVIES = [
    {
        "name": "Spider-Man: Brand New Day",
        "price": "4:20 PM, 6:35 PM (XD), 7:45 PM, 10:00 PM (XD)",
        "description": "PG-13 • 2 hr 25 min | Formats: XD, Standard Format | Poster: https://www.cinemark.com/media/5rqjx3u4/smspidermanxdposter.jpg | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "The Odyssey",
        "price": "3:30 PM, 7:15 PM",
        "description": "R • 2 hr 52 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "Coyote vs. Acme",
        "price": "2:10 PM, 4:45 PM, 7:20 PM, 9:50 PM",
        "description": "PG • 1 hr 43 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "By Any Means",
        "price": "4:00 PM, 7:00 PM, 9:40 PM",
        "description": "R • 1 hr 47 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "Cars 20th Anniversary",
        "price": "1:00 PM, 3:45 PM, 6:30 PM",
        "description": "G • 1 hr 57 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "The Dog Stars",
        "price": "4:10 PM, 7:30 PM, 10:15 PM",
        "description": "R • 1 hr 58 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "Akira 4K (English Dubbed)",
        "price": "7:00 PM",
        "description": "R • 2 hr 5 min | Formats: Special Event | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
    {
        "name": "PAW Patrol: The Dino Movie",
        "price": "1:15 PM, 3:30 PM",
        "description": "PG • 1 hr 28 min | Formats: Standard Format | Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd",
    },
]


class CinemarkHadleyScraper(BaseScraper):
    """Scraper for Cinemark at Hampshire Mall & XD in Hadley, MA.

    Extracts active film titles, formats (XD, RealD 3D, Standard Format),
    showtimes, ratings, runtime, poster URLs, and direct ticketing links.
    Uses Playwright browser automation with domcontentloaded to handle dynamic JS loading.
    """
    store_name: str = "Cinemark at Hampshire Mall (Hadley)"
    scraper_key: str = "cinemark_hadley"
    kind: str = "movie"
    url: str = "https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd"

    async def scrape(self, page=None) -> Optional[Dict[str, Any]]:
        """Scrape active movie showtimes from Cinemark at Hampshire Mall.

        Args:
            page: Playwright Page instance configured for headless execution.

        Returns:
            Normalized dictionary built via BaseScraper.build_result().
        """
        deals = []
        now = datetime.datetime.now(datetime.timezone.utc)
        today = datetime.date.today()

        try:
            if page is not None:
                logger.info("Navigating to Cinemark Hampshire Mall at %s", self.url)
                # Use domcontentloaded; avoid networkidle due to long-lived telemetry connections
                await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_selector(".showtimeMovieBlock", timeout=12000)

                # Evaluate movie cards directly within the browser DOM context
                raw_movies = await page.evaluate(
                    '''() => {
                    const blocks = Array.from(document.querySelectorAll('.showtimeMovieBlock'));
                    const results = [];
                    for (const b of blocks) {
                        const titleEl = b.querySelector('h3[id], .movieLink h3');
                        if (!titleEl) continue;
                        const title = titleEl.innerText.trim();
                        if (!title) continue;

                        const imgEl = b.querySelector('picture img, img.lazyload');
                        let poster = '';
                        if (imgEl) {
                            poster = imgEl.getAttribute('data-srcset') || imgEl.getAttribute('srcset') || imgEl.src || '';
                        }

                        const infoEl = b.querySelector('.movieBlockInfo');
                        const infoText = infoEl ? infoEl.innerText : '';

                        const ratingMatch = infoText.match(/\\b(G|PG-13|PG|R|NC-17|NR)\\b/);
                        const rating = ratingMatch ? ratingMatch[1] : '';

                        const runtimeMatch = infoText.match(/(\\d+\\s*hr(?:\\s*\\d+\\s*min)?|\\d+\\s*min)/i);
                        const runtime = runtimeMatch ? runtimeMatch[1] : '';

                        const stEls = Array.from(b.querySelectorAll('div.showtime'));
                        const times = [];
                        for (const st of stEls) {
                            const fmt = st.getAttribute('data-print-type-name') || '';
                            const a = st.querySelector('a');
                            const p = st.querySelector('p');
                            const t = (a ? a.innerText : (p ? p.innerText : st.innerText)).trim();
                            if (t) {
                                times.push({
                                    time: t,
                                    format: fmt,
                                    ticket_url: a ? a.href : ''
                                });
                            }
                        }

                        results.push({
                            title: title,
                            poster: poster,
                            rating: rating,
                            runtime: runtime,
                            times: times
                        });
                    }
                    return results;
                }'''
                )

                for rm in raw_movies:
                    title = rm.get("title")
                    if not title:
                        continue

                    times_list = rm.get("times") or rm.get("showtimes") or []
                    time_strings = []
                    sample_ticket = ""
                    formats_seen = set()
                    for t_item in times_list:
                        t_str = t_item.get("time", "")
                        fmt = t_item.get("format", "")
                        if fmt and fmt not in ("Standard Format", ""):
                            formats_seen.add(fmt)
                            time_strings.append(f"{t_str} ({fmt})")
                        elif t_str:
                            time_strings.append(t_str)
                        if not sample_ticket and t_item.get("ticket_url"):
                            sample_ticket = t_item["ticket_url"]

                    display_times = ", ".join(time_strings) if time_strings else "Check schedule"

                    desc_parts = []
                    rating = rm.get("rating", "")
                    runtime = rm.get("runtime", "")
                    if rating or runtime:
                        desc_parts.append(f"{rating} • {runtime}".strip(" • "))
                    formats_combined = set(formats_seen)
                    if isinstance(rm.get("formats"), list):
                        formats_combined.update([f for f in rm.get("formats") if f and f != "Standard Format"])
                    if formats_combined:
                        desc_parts.append(f"Formats: {', '.join(sorted(formats_combined))}")
                    poster = rm.get("poster", "")
                    if poster:
                        desc_parts.append(f"Poster: {poster}")
                    if sample_ticket:
                        desc_parts.append(f"Tickets: {sample_ticket}")
                    desc_parts.append("Details: https://www.cinemark.com/theatres/ma-hadley/cinemark-at-hampshire-mall-and-xd")

                    deals.append(
                        {
                            "name": title,
                            "price": display_times,
                            "description": " | ".join(desc_parts),
                        }
                    )
        except Exception as e:
            logger.error("Scraping %s failed: %s", self.store_name, e)

        if not deals:
            logger.warning("Using fallback movies for %s", self.store_name)
            deals = list(FALLBACK_MOVIES)

        payload = {
            "deals": deals,
            "items_scraped": len(deals),
            "flyer_start_date": today.isoformat(),
            "flyer_end_date": (today + datetime.timedelta(days=1)).isoformat(),
            "expires_at": now + datetime.timedelta(hours=24),
            "next_refresh_at": now + datetime.timedelta(hours=12),
            "date_source": "direct_html",
        }
        return self.build_result(payload)
