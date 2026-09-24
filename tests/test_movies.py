import datetime
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.scrapers.greenfield_garden_cinemas import (
    GreenfieldGardenCinemasScraper,
    FALLBACK_MOVIES as GARDEN_FALLBACK_MOVIES,
)
from app.scrapers.cinemark_hadley import (
    CinemarkHadleyScraper,
    FALLBACK_MOVIES as CINEMARK_FALLBACK_MOVIES,
)


@pytest.mark.asyncio
async def test_greenfield_garden_cinemas_fallback():
    """Verify Greenfield Garden Cinemas scraper uses curated fallback deals on network failure."""
    scraper = GreenfieldGardenCinemasScraper()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Connection refused")

    with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
        result = await scraper.scrape(mock_page)

    assert result is not None
    assert result["kind"] == "movie"
    assert result["store_name"] == "Greenfield Garden Cinemas"
    assert result["scraper_key"] == "greenfield_garden_cinemas"
    assert len(result["deals"]) == len(GARDEN_FALLBACK_MOVIES)
    for deal in result["deals"]:
        assert deal["name"]
        assert deal["price"]
        assert "gardencinemas.net" in deal["description"]


def test_greenfield_garden_cinemas_parse_html():
    """Verify HTML parsing correctly extracts titles, showtimes, ratings, director, cast, and tickets."""
    scraper = GreenfieldGardenCinemasScraper()
    sample_html = """
    <div class="row listitem">
        <div class="col-sm-4"><img src="images/test_poster.jpg" alt="Poster"></div>
        <div class="col-sm-8">
            <h3 class="title">Test Movie Odyssey</h3>
            <span class="rating">PG-13</span>
            <span class="runtime">124 min</span>
            <span class="genre">Sci-Fi</span>
            <span class="director">Director: Jane Doe</span>
            <span class="starring">Starring: Actor One, Actor Two</span>
            <div class="showtimes">
                <a class="nolink" href="https://formovietickets.com/test1">4:30 PM</a>
                <a class="nolink" href="https://formovietickets.com/test2">7:15 PM</a>
            </div>
            <button class="trailer-modal" data-url="https://youtube.com/watch?v=123">Trailer</button>
        </div>
    </div>
    """
    deals = scraper._parse_html(sample_html)
    assert len(deals) == 1
    movie = deals[0]
    assert movie["name"] == "Test Movie Odyssey"
    assert "4:30 PM" in movie["price"]
    assert "7:15 PM" in movie["price"]
    assert "PG-13 • 124 min" in movie["description"]
    assert "Director: Jane Doe" in movie["description"]
    assert "Starring: Actor One, Actor Two" in movie["description"]
    assert "Trailer: https://youtube.com/watch?v=123" in movie["description"]
    assert "Tickets: https://formovietickets.com/test1" in movie["description"]


@pytest.mark.asyncio
async def test_cinemark_hadley_fallback():
    """Verify Cinemark Hampshire Mall scraper uses curated fallback deals on browser failure."""
    scraper = CinemarkHadleyScraper()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Timeout loading Cinemark")

    result = await scraper.scrape(mock_page)

    assert result is not None
    assert result["kind"] == "movie"
    assert result["store_name"] == "Cinemark at Hampshire Mall (Hadley)"
    assert result["scraper_key"] == "cinemark_hadley"
    assert len(result["deals"]) == len(CINEMARK_FALLBACK_MOVIES)
    for deal in result["deals"]:
        assert deal["name"]
        assert deal["price"]
        assert "cinemark.com" in deal["description"]


@pytest.mark.asyncio
async def test_cinemark_hadley_evaluate_parsing():
    """Verify evaluated in-browser DOM objects are formatted into deals with formats and ticket URLs."""
    scraper = CinemarkHadleyScraper()
    mock_page = AsyncMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None

    mock_evaluated = [
        {
            "title": "Spider-Man 4",
            "poster": "https://media.cinemark.com/spiderman.jpg",
            "rating": "PG-13",
            "runtime": "2 hr 10 min",
            "formats": ["XD"],
            "showtimes": [
                {"time": "3:00 PM", "format": "Standard Format", "ticket_url": "https://cinemark.com/ticket1"},
                {"time": "6:30 PM", "format": "XD", "ticket_url": "https://cinemark.com/ticket2"},
            ],
        }
    ]
    mock_page.evaluate.return_value = mock_evaluated

    result = await scraper.scrape(mock_page)

    assert result is not None
    assert len(result["deals"]) == 1
    deal = result["deals"][0]
    assert deal["name"] == "Spider-Man 4"
    assert "3:00 PM" in deal["price"]
    assert "6:30 PM (XD)" in deal["price"]
    assert "PG-13 • 2 hr 10 min" in deal["description"]
    assert "Formats: XD" in deal["description"]
    assert "Tickets: https://cinemark.com/ticket1" in deal["description"]


def test_movies_route_renders_active_datasets():
    """Verify /movies endpoint returns status 200 and renders theater branding cards."""
    client = TestClient(app)
    response = client.get("/movies")
    assert response.status_code == 200
    assert "Movie Showtimes" in response.text
    assert "Now Playing in the Valley" in response.text
    assert "Greenfield Garden Cinemas" in response.text
    assert "Cinemark at Hampshire Mall" in response.text


def test_interleave_wheel_items():
    """Verify wheel items interleave events and movies evenly around the wheel."""
    from app.main import _interleave_wheel_items

    events = [{"title": f"Event {i}", "is_movie": False} for i in range(5)]
    movies = [{"title": f"Movie {i}", "is_movie": True} for i in range(5)]

    interleaved = _interleave_wheel_items(events, movies)
    assert len(interleaved) == 10
    # Slices alternate between events and movies
    assert interleaved[0]["is_movie"] != interleaved[1]["is_movie"]


def test_events_wheel_includes_upcoming_movies():
    """Verify /events route includes the wheel component and ticketing action links."""
    client = TestClient(app)
    response = client.get("/events")
    assert response.status_code == 200
    assert "Today&#39;s Activity Wheel" in response.text or "Today's Activity Wheel" in response.text
    assert "today-events-json" in response.text
    assert "winner-ticket-link" in response.text


def test_upcoming_wheel_movies_filters_and_caps():
    """Verify activity wheel movies strictly bound showtimes within 2.5h, deduplicate, and cap at 8."""
    import zoneinfo
    from app.main import _get_upcoming_wheel_movies
    from app.database import get_db
    from app.store_utils import get_active_movie_datasets

    db = next(get_db())
    tz = zoneinfo.ZoneInfo("America/New_York")
    active = get_active_movie_datasets(db)
    if active and active[0].flyer_start_date:
        ref_time = datetime.datetime.combine(active[0].flyer_start_date, datetime.time(16, 15), tzinfo=tz)
    else:
        ref_time = datetime.datetime.now(tz).replace(hour=16, minute=15, second=0, microsecond=0)

    # Within 2.5 hours, capped at 8
    movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=2.5, max_movies=8, now_ref=ref_time)
    assert 0 < len(movies) <= 8

    # All returned movies must have showtimes within the allowed window
    min_allowed = ref_time - datetime.timedelta(minutes=10)
    max_allowed = ref_time + datetime.timedelta(hours=2.5)
    for m in movies:
        assert m["is_movie"] is True
        assert min_allowed <= m["next_dt"] <= max_allowed

    # Unique titles (deduplication across venues)
    titles = [m["pure_title"].lower() for m in movies]
    assert len(titles) == len(set(titles))

    # Tighter window: 30 minutes
    narrow_movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=0.5, max_movies=8, now_ref=ref_time)
    for m in narrow_movies:
        assert m["next_dt"] <= ref_time + datetime.timedelta(hours=0.5)

