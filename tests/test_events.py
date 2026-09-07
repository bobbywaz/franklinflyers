import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.scrapers.shea_theater import SheaTheaterScraper
from app.scrapers.tree_house import TreeHouseScraper
from app.scrapers.rendezvous import RendezvousScraper
from app.scrapers.four_phantoms import FourPhantomsScraper
from app.scrapers.visit_greenfield import VisitGreenfieldScraper
from app.store_utils import parse_date_value


def test_parse_date_value_september_abbreviation():
    """Verify parse_date_value correctly parses 'Sept', 'Sep', and 'September' date formats."""
    ref_date = datetime.date(2026, 9, 6)
    assert parse_date_value("Sept 9", ref_date) == datetime.date(2026, 9, 9)
    assert parse_date_value("Sep 9", ref_date) == datetime.date(2026, 9, 9)
    assert parse_date_value("September 9", ref_date) == datetime.date(2026, 9, 9)


@pytest.mark.asyncio
async def test_shea_theater_scrape_fallback():
    """Verify Shea Theater scraper produces resilient fallback events on timeout/error."""
    scraper = SheaTheaterScraper()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Page timeout")

    result = await scraper.scrape(mock_page)
    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "Shea Theater"
    assert len(result["deals"]) >= 4
    for deal in result["deals"]:
        assert deal["name"]
        assert deal["price"]
        assert "Details: https://sheatheater.org" in deal["description"]


@pytest.mark.asyncio
async def test_tree_house_scrape_fallback():
    """Verify Tree House Deerfield scraper produces resilient fallback events on timeout/error."""
    scraper = TreeHouseScraper()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Page timeout")

    result = await scraper.scrape(mock_page)
    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "Tree House Brewing (South Deerfield)"
    assert len(result["deals"]) >= 3
    for deal in result["deals"]:
        assert "Until" in deal["price"]
        assert "treehousebrew.com" in deal["description"]


@pytest.mark.asyncio
async def test_rendezvous_scrape_produces_recurring_deals():
    """Verify The Rendezvous scraper produces structured recurring weekly community events."""
    scraper = RendezvousScraper()
    mock_page = AsyncMock()

    result = await scraper.scrape(mock_page)
    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "The Rendezvous"
    assert len(result["deals"]) >= 5
    for deal in result["deals"]:
        assert "Every" in deal["price"]
        assert "Until" in deal["price"]
        assert "thevoo.net" in deal["description"]


@pytest.mark.asyncio
async def test_four_phantoms_scrape_produces_recurring_deals():
    """Verify Four Phantoms scraper produces structured recurring taproom events."""
    scraper = FourPhantomsScraper()
    mock_page = AsyncMock()

    result = await scraper.scrape(mock_page)
    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "Four Phantoms Brewing"
    assert len(result["deals"]) >= 3
    for deal in result["deals"]:
        assert "Every" in deal["price"]
        assert "Until" in deal["price"]
        assert "fourphantoms.com" in deal["description"]


def test_events_template_renders_card_anchors():
    """Verify calendar items render as deep links to matching event cards below."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    test_events = [
        {
            "id": 101,
            "store_name": "Shea Theater",
            "title": "Concert 1",
            "datetime_label": "Sept 12, 2026",
            "description": "A live show",
            "event_date": datetime.date(2026, 9, 12),
            "detail_url": "https://sheatheater.org/1",
        }
    ]
    html = template.render(
        has_data=True,
        all_events=test_events,
        undated_events=[],
        calendar_events={"2026-09-12": test_events},
        calendar_weeks=[[datetime.date(2026, 9, 12)]],
        calendar_first_date=datetime.date(2026, 9, 12),
        calendar_last_date=datetime.date(2026, 9, 12),
        today=datetime.date(2026, 9, 6),
        active_store_badges=[],
    )
    assert 'href="#event-101"' in html
    assert 'id="event-101"' in html
    assert "event-card-target" in html


def test_events_template_renders_today_activity_wheel():
    """Verify activity wheel HTML structure, spin controls, and embedded JSON are rendered."""
    import json
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 9, 6)
    today_event = {
        "id": 202,
        "store_name": "Shea Theater",
        "title": "Sunday Show",
        "datetime_label": "Sept 6, 2026, 7:00 PM",
        "description": "Fun night",
        "event_date": today,
        "detail_url": "https://sheatheater.org/shows/202",
    }
    today_events = [today_event]
    today_events_json = json.dumps([
        {
            "id": today_event["id"],
            "title": today_event["title"],
            "store_name": today_event["store_name"],
            "datetime_label": today_event["datetime_label"],
            "description": today_event["description"],
            "detail_url": today_event["detail_url"],
        }
    ])
    html = template.render(
        has_data=True,
        all_events=today_events,
        undated_events=[],
        calendar_events={"2026-09-06": today_events},
        calendar_weeks=[[today]],
        calendar_first_date=today,
        calendar_last_date=today,
        today=today,
        today_events=today_events,
        today_events_json=today_events_json,
        active_store_badges=[],
    )
    assert 'id="wheel-section"' in html
    assert 'id="activity-wheel"' in html
    assert 'id="spin-btn"' in html
    assert 'id="wheel-center-btn"' in html
    assert 'id="today-events-json"' in html
    assert "Sunday Show" in html
    assert html.find('id="calendar-heading"') < html.find('id="wheel-heading"') < html.find('Upcoming Live Events')


@pytest.mark.asyncio
async def test_visit_greenfield_scrape_api():
    """Verify Visit Greenfield scraper extracts and normalizes Tribe REST API events."""
    from unittest.mock import patch, MagicMock

    mock_events_data = {
        "events": [
            {
                "title": "GPL Lego Club (drop-in)",
                "start_date": "2026-09-07 15:30:00",
                "end_date": "2026-09-07 17:00:00",
                "all_day": False,
                "url": "https://visitgreenfieldma.com/event/gpl-lego-club-drop-in/",
                "venue": {
                    "venue": "Greenfield Public Library",
                    "address": "412 Main St",
                    "city": "Greenfield",
                },
                "description": "<p>Come be a part of the kids GPL Lego Club!</p>",
            },
            {
                "title": "Greenfield Farmers Market",
                "start_date": "2026-09-12 08:00:00",
                "end_date": "2026-09-12 12:30:00",
                "all_day": True,
                "url": "https://visitgreenfieldma.com/event/greenfield-farmers-market/",
                "venue": {
                    "venue": "Court Square",
                    "address": "Court Sq",
                    "city": "Greenfield",
                },
                "description": "<p>Fresh local produce, crafts, and baked goods.</p>",
            },
        ]
    }

    scraper = VisitGreenfieldScraper()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_events_data

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await scraper.scrape(AsyncMock())

    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "Visit Greenfield Events"
    assert len(result["deals"]) == 2

    lego_deal = result["deals"][0]
    assert lego_deal["name"] == "GPL Lego Club (drop-in)"
    assert "Monday, September 7, 2026 at 3:30 PM" in lego_deal["price"]
    assert "Greenfield Public Library" in lego_deal["description"]
    assert "Details: https://visitgreenfieldma.com/event/gpl-lego-club-drop-in/" in lego_deal["description"]

    market_deal = result["deals"][1]
    assert market_deal["name"] == "Greenfield Farmers Market"
    assert "Saturday, September 12, 2026 - All Day" in market_deal["price"]
    assert "Court Square" in market_deal["description"]
    assert "Details: https://visitgreenfieldma.com/event/greenfield-farmers-market/" in market_deal["description"]


@pytest.mark.asyncio
async def test_visit_greenfield_scrape_fallback():
    """Verify Visit Greenfield scraper falls back gracefully to curated community events."""
    scraper = VisitGreenfieldScraper()
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Browser failed")

    with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
        result = await scraper.scrape(mock_page)

    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "Visit Greenfield Events"
    assert len(result["deals"]) >= 5
    deal_names = [d["name"] for d in result["deals"]]
    assert any("Farmers" in name for name in deal_names)
    assert any("Library" in name for name in deal_names)
    for deal in result["deals"]:
        assert "Details: https://visitgreenfieldma.com/events/" in deal["description"]


def test_events_template_renders_visit_greenfield():
    """Verify events template renders Visit Greenfield badges and venue card."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 9, 6)
    vg_event = {
        "id": 301,
        "store_name": "Visit Greenfield Events",
        "title": "GPL Lego Club",
        "datetime_label": "Sept 7, 2026, 3:30 PM",
        "description": "Greenfield Public Library | Building session",
        "event_date": datetime.date(2026, 9, 7),
        "detail_url": "https://visitgreenfieldma.com/event/lego",
    }
    html = template.render(
        has_data=True,
        all_events=[vg_event],
        undated_events=[],
        calendar_events={"2026-09-07": [vg_event]},
        calendar_weeks=[[datetime.date(2026, 9, 7)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=7),
        today=today,
        today_events=[],
        active_store_badges=[
            {
                "name": "Visit Greenfield Events",
                "range_label": "Sep 6 - Sep 20",
                "scraper_key": "visit_greenfield",
                "flyer_url": "https://visitgreenfieldma.com/events/",
            }
        ],
    )
    assert "Visit Greenfield Events" in html
    assert "bg-visit-greenfield" in html
    assert "https://visitgreenfieldma.com/events/" in html
    assert "Open Greenfield Events" in html


