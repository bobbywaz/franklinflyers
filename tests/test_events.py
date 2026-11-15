import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.scrapers.shea_theater import SheaTheaterScraper
from app.scrapers.tree_house import TreeHouseScraper
from app.scrapers.rendezvous import RendezvousScraper
from app.scrapers.four_phantoms import FourPhantomsScraper
from app.scrapers.visit_greenfield import VisitGreenfieldScraper
from app.scrapers.river_culture import RiverCultureScraper
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
        assert "fourphantoms.net" in deal["description"]


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

    fixed_now = datetime.datetime(2026, 9, 6, 12, 0, tzinfo=datetime.timezone.utc)
    with patch("app.scrapers.visit_greenfield.utcnow", return_value=fixed_now):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await scraper.scrape(None)

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


@pytest.mark.asyncio
async def test_river_culture_scrape():
    """Verify RiverCulture scraper produces structured events for Turners Falls / Montague."""
    scraper = RiverCultureScraper()
    result = await scraper.scrape(page=None)
    assert result is not None
    assert result["kind"] == "event"
    assert result["store_name"] == "RiverCulture Turners Falls"
    assert result["scraper_key"] == "river_culture"
    assert len(result["deals"]) >= 4
    for deal in result["deals"]:
        assert deal["name"]
        assert deal["price"]
        assert "Details:" in deal["description"]


def test_events_template_renders_river_culture():
    """Verify events template renders RiverCulture badges, venue card, and color dot."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 10, 3)
    rc_event = {
        "id": 401,
        "store_name": "RiverCulture Turners Falls",
        "title": "First Friday Turners Falls",
        "datetime_label": "Friday, October 9, 5:00 PM - 8:00 PM",
        "description": "Avenue A | Art walk & live music | Details: https://www.riverculture.org",
        "event_date": datetime.date(2026, 10, 9),
        "detail_url": "https://www.riverculture.org",
    }
    html = template.render(
        has_data=True,
        all_events=[rc_event],
        undated_events=[],
        calendar_events={"2026-10-09": [rc_event]},
        calendar_weeks=[[datetime.date(2026, 10, 9)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=7),
        today=today,
        today_events=[],
        active_store_badges=[
            {
                "name": "RiverCulture Turners Falls",
                "range_label": "Oct 3 - Oct 17",
                "scraper_key": "river_culture",
                "flyer_url": "https://www.riverculture.org",
            }
        ],
    )
    assert "RiverCulture Turners Falls" in html
    assert "bg-river-culture" in html
    assert "https://www.riverculture.org" in html
    assert "Visit Website &amp; Events" in html or "Visit Website & Events" in html


@pytest.mark.asyncio
async def test_drake_amherst_scrape():
    """Verify DrakeAmherstScraper extracts structured events, dates, and build_result."""
    from app.scrapers.drake_amherst import DrakeAmherstScraper

    scraper = DrakeAmherstScraper()
    assert scraper.scraper_key == "drake_amherst"
    assert scraper.kind == "event"
    assert scraper.store_name == "The Drake Amherst"

    res = await scraper.scrape()
    assert res is not None
    assert res["kind"] == "event"
    assert res["store_name"] == "The Drake Amherst"
    assert res["scraper_key"] == "drake_amherst"
    assert len(res["deals"]) >= 3
    assert res["items_scraped_count"] == len(res["deals"])

    sample = res["deals"][0]
    assert "name" in sample
    assert "price" in sample
    assert "description" in sample
    assert "Details:" in sample["description"]


def test_events_template_renders_drake_and_multiline_title():
    """Verify The Drake Amherst renders in template and calendar event title is multi-line with no source line."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 10, 3)
    drake_event = {
        "id": 501,
        "store_name": "The Drake Amherst",
        "title": "ARHS Fundraiser - A Beatles Immersive Sing-along",
        "datetime_label": "October 06, 2026 07:00 PM",
        "description": "ARHS performing arts staff leads an immersive Beatles-themed sing-along experience | Details: https://www.thedrakeamherst.org/events/arhs-fundraiser-beatles-sing-along",
        "event_date": datetime.date(2026, 10, 6),
        "detail_url": "https://www.thedrakeamherst.org/events/arhs-fundraiser-beatles-sing-along",
    }
    html = template.render(
        has_data=True,
        all_events=[drake_event],
        undated_events=[],
        calendar_events={"2026-10-06": [drake_event]},
        calendar_weeks=[[datetime.date(2026, 10, 6)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=7),
        today=today,
        today_events=[],
        active_store_badges=[
            {
                "name": "The Drake Amherst",
                "range_label": "Oct 3 - Oct 20",
                "scraper_key": "drake_amherst",
                "flyer_url": "https://www.thedrakeamherst.org",
            }
        ],
    )
    assert "The Drake Amherst" in html
    assert "bg-drake" in html
    assert "border-drake_amherst" in html
    assert "https://www.thedrakeamherst.org" in html
    assert "line-clamp-3" in html
    assert "ARHS Fundraiser - A Beatles Immersive Sing-along" in html
    # Ensure event source is NOT rendered below title in calendar cell
    assert '<span class="inline-block h-1.5 w-1.5 rounded-full' not in html
    assert '<span class="inline-block h-2 w-2 rounded-full bg-drake' in html


@pytest.mark.asyncio
async def test_iron_horse_scrape_api():
    """Verify Iron Horse scraper parses events from Elfsight calendar API."""
    from unittest.mock import patch, MagicMock
    from app.scrapers.iron_horse import IronHorseScraper

    mock_elfsight_payload = {
        "status": True,
        "data": {
            "widgets": {
                "c4b76df1-e520-4ed0-9318-f18bd056c38a": {
                    "data": {
                        "settings": {
                            "events": [
                                {
                                    "id": "ev-1",
                                    "name": "Katie Pruitt - Fools for the Fleeting Tour",
                                    "start": {
                                        "date": "2026-10-15",
                                        "time": "19:00",
                                    },
                                    "description": "<p>Live at The Iron Horse Music Hall</p>",
                                    "location": ["loc-1"],
                                    "actions": [
                                        {
                                            "link": {
                                                "value": "https://theparlorroom.my.salesforce-sites.com/ticket/#/events/1"
                                            }
                                        }
                                    ],
                                }
                            ],
                            "locations": [
                                {
                                    "id": "loc-1",
                                    "name": "THE IRON HORSE",
                                    "address": "18 Center St, Northampton MA",
                                }
                            ],
                        }
                    }
                }
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_elfsight_payload

    import datetime
    fixed_now = datetime.datetime(2026, 10, 15, 0, 0, 0)
    with patch("app.scrapers.iron_horse.utcnow", return_value=fixed_now), patch("httpx.AsyncClient.get", return_value=mock_resp):
        scraper = IronHorseScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["items_scraped_count"] >= 1
    assert any("Katie Pruitt" in d["name"] for d in result["deals"])
    pruitt_deal = next(d for d in result["deals"] if "Katie Pruitt" in d["name"])
    assert "THE IRON HORSE" in pruitt_deal["description"]
    assert "https://theparlorroom.my.salesforce-sites.com" in pruitt_deal["description"]
    assert "October 15, 2026 7:00 PM" in pruitt_deal["price"]


def test_events_template_renders_iron_horse():
    """Verify The Iron Horse renders in template with badges and styles."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 10, 3)
    ih_event = {
        "id": 601,
        "store_name": "The Iron Horse",
        "title": "An Evening with Maria Muldaur",
        "datetime_label": "October 07, 2026 07:00 PM",
        "description": "Location: THE IRON HORSE | Details: https://theparlorroom.my.salesforce-sites.com/ticket/#/events/2",
        "event_date": datetime.date(2026, 10, 7),
        "detail_url": "https://theparlorroom.my.salesforce-sites.com/ticket/#/events/2",
    }
    html = template.render(
        has_data=True,
        all_events=[ih_event],
        undated_events=[],
        calendar_events={"2026-10-07": [ih_event]},
        calendar_weeks=[[datetime.date(2026, 10, 7)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=7),
        today=today,
        today_events=[],
        active_store_badges=[
            {
                "name": "The Iron Horse",
                "range_label": "Oct 3 - Nov 15",
                "scraper_key": "iron_horse",
                "flyer_url": "https://www.ironhorse.org",
            }
        ],
    )
    assert "The Iron Horse" in html
    assert "bg-iron-horse" in html
    assert "border-iron_horse" in html
    assert "https://www.ironhorse.org" in html
    assert "An Evening with Maria Muldaur" in html


@pytest.mark.asyncio
async def test_luthiers_coop_scrape_api():
    """Verify Luthiers Co-op scraper parses events from Tribe Events REST API."""
    from unittest.mock import patch, MagicMock
    from app.scrapers.luthiers_coop import LuthiersCoopScraper

    from app.store_utils import utcnow
    today_dt = utcnow()
    d1 = today_dt + datetime.timedelta(days=1)
    d1_str = d1.strftime("%Y-%m-%d 19:00:00")
    d1_label = d1.strftime("%B %d, %Y").replace(" 0", " ")

    mock_tribe_payload = {
        "events": [
            {
                "id": 101,
                "title": "Robert LaRoche, 7-8pm",
                "start_date": d1_str,
                "url": "https://www.luthiers-coop.com/event/robert-laroche-7-8pm/",
                "description": "<p>Legendary local rock/pop songwriter</p>",
            },
            {
                "id": 102,
                "title": "CLOSED",
                "start_date": (today_dt + datetime.timedelta(days=2)).strftime("%Y-%m-%d 18:00:00"),
                "url": "https://www.luthiers-coop.com/event/closed/",
                "description": "",
            },
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_tribe_payload

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        scraper = LuthiersCoopScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["items_scraped_count"] >= 1
    assert any("Robert LaRoche" in d["name"] for d in result["deals"])
    assert not any(d["name"].upper() == "CLOSED" for d in result["deals"])
    deal = next(d for d in result["deals"] if "Robert LaRoche" in d["name"])
    assert "108 Cottage St, Easthampton, MA" in deal["description"]
    assert d1_label in deal["price"]


@pytest.mark.asyncio
async def test_marigold_theater_scrape():
    """Verify Marigold Theater scraper parses gallery grid HTML."""
    from unittest.mock import patch, MagicMock
    from app.scrapers.marigold_theater import MarigoldTheaterScraper

    mock_html = """
    <div class="wonderplugin-gridgallery-item">
        <a href="https://marigold.org/blues-night-with-electric-delta/" data-title="SAT OCT 17" data-description="BLUES NIGHT FEAT. ELECTRIC DELTA Join us for blues fusion">
            <img src="https://marigold.org/img.png" />
        </a>
        <div class="wonderplugin-gridgallery-item-caption-title">SAT OCT 17</div>
    </div>
    """

    import datetime
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    fixed_now = datetime.datetime(2026, 10, 17, 0, 0, 0)
    with patch("app.scrapers.marigold_theater.utcnow", return_value=fixed_now), patch("httpx.AsyncClient.get", return_value=mock_resp):
        scraper = MarigoldTheaterScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["items_scraped_count"] >= 1
    assert any("Electric Delta" in d["name"] or "Blues Night" in d["name"] for d in result["deals"])
    deal = next(d for d in result["deals"] if "Electric Delta" in d["name"] or "Blues Night" in d["name"])
    assert "84 Cottage St, Easthampton, MA" in deal["description"]
    assert "October 17, 2026" in deal["price"]


@pytest.mark.asyncio
async def test_incandescent_brewing_scrape_api():
    """Verify Incandescent Brewing scraper parses Squarespace JSON events."""
    from unittest.mock import patch, MagicMock
    from app.scrapers.incandescent_brewing import IncandescentBrewingScraper

    future_ms = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).timestamp() * 1000)
    mock_sqsp_payload = {
        "upcoming": [
            {
                "title": "TRIVIA NIGHT with TALARICO TRIVIA",
                "startDate": future_ms,
                "fullUrl": "/events/trivia-night",
                "excerpt": "<p>Five rounds of eclectic barroom trivia with host Talarico</p>",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_sqsp_payload

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        scraper = IncandescentBrewingScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["items_scraped_count"] >= 1
    assert any("TALARICO TRIVIA" in d["name"] for d in result["deals"])
    deal = next(d for d in result["deals"] if "TALARICO TRIVIA" in d["name"])
    assert "16 French King Hwy, Gill, MA" in deal["description"]
    assert "https://www.incandescentbrewing.com/events/trivia-night" in deal["description"]


def test_events_template_renders_three_new_venues():
    """Verify Luthiers Co-op, Marigold Theater, and Incandescent Brewing render in template."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 10, 3)

    events_list = [
        {
            "id": 701,
            "store_name": "The Luthier's Co-op",
            "title": "Lonesome Brothers",
            "datetime_label": "October 10, 2026 8:00 PM",
            "description": "Location: The Luthier's Co-op, 108 Cottage St | Details: https://www.luthiers-coop.com/events/",
            "event_date": datetime.date(2026, 10, 10),
            "detail_url": "https://www.luthiers-coop.com/events/",
        },
        {
            "id": 702,
            "store_name": "Marigold Theater",
            "title": "Salsa Sundays",
            "datetime_label": "October 11, 2026",
            "description": "Location: Marigold Theater, 84 Cottage St | Details: https://marigold.org/",
            "event_date": datetime.date(2026, 10, 11),
            "detail_url": "https://marigold.org/",
        },
        {
            "id": 703,
            "store_name": "Incandescent Brewing",
            "title": "Oktoberfest",
            "datetime_label": "October 12, 2026 12:00 PM",
            "description": "Location: Incandescent Brewing, 16 French King Hwy | Details: https://www.incandescentbrewing.com/events",
            "event_date": datetime.date(2026, 10, 12),
            "detail_url": "https://www.incandescentbrewing.com/events",
        },
    ]

    html = template.render(
        has_data=True,
        all_events=events_list,
        undated_events=[],
        calendar_events={
            "2026-10-10": [events_list[0]],
            "2026-10-11": [events_list[1]],
            "2026-10-12": [events_list[2]],
        },
        calendar_weeks=[[datetime.date(2026, 10, 10), datetime.date(2026, 10, 11), datetime.date(2026, 10, 12)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=14),
        today=today,
        today_events=[],
        active_store_badges=[
            {"name": "The Luthier's Co-op", "scraper_key": "luthiers_coop", "flyer_url": "https://www.luthiers-coop.com/events/", "range_label": "Oct 3 - Nov 3"},
            {"name": "Marigold Theater", "scraper_key": "marigold_theater", "flyer_url": "https://marigold.org/", "range_label": "Oct 3 - Nov 3"},
            {"name": "Incandescent Brewing", "scraper_key": "incandescent_brewing", "flyer_url": "https://www.incandescentbrewing.com/events", "range_label": "Oct 3 - Nov 3"},
        ],
    )

    assert "The Luthier's Co-op" in html
    assert "bg-luthiers-coop" in html
    assert "border-luthiers_coop" in html
    assert "Marigold Theater" in html
    assert "bg-marigold" in html
    assert "border-marigold_theater" in html
    assert "Incandescent Brewing" in html
    assert "bg-incandescent" in html
    assert "border-incandescent_brewing" in html
    assert "Lonesome Brothers" in html
    assert "Salsa Sundays" in html
    assert "Oktoberfest" in html


@pytest.mark.asyncio
async def test_bears_den_scrape_warmup():
    """Verify Bears Den scraper extracts events from Wix warmup data."""
    import json
    from app.scrapers.bears_den import BearsDenScraper

    from app.store_utils import utcnow
    today_dt = utcnow()
    d1_iso = (today_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%dT23:00:00.000Z")
    d1_fmt = (today_dt + datetime.timedelta(days=1)).strftime("%B %d, %Y, 7:00 – 9:00 PM")
    d2_iso = (today_dt + datetime.timedelta(days=5)).strftime("%Y-%m-%dT23:00:00.000Z")
    d2_fmt = (today_dt + datetime.timedelta(days=5)).strftime("%B %d, %Y, 7:00 – 11:00 PM")

    mock_warmup_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <script id="wix-warmup-data" type="application/json">
    {{
        "appsWarmupData": {{
            "app123": {{
                "widget123": {{
                    "events": {{
                        "events": [
                            {{
                                "title": "Live Music! Lexi Weege",
                                "slug": "live-music-lexi-weege",
                                "description": "Lexi Weege will be playing live on the patio!",
                                "scheduling": {{
                                    "config": {{
                                        "startDate": "{d1_iso}",
                                        "timeZoneId": "America/New_York"
                                    }},
                                    "formatted": "{d1_fmt}"
                                }}
                            }},
                            {{
                                "title": "Karaoke Night",
                                "slug": "karaoke-night-oct-14",
                                "description": "Sing your heart out with Robin!",
                                "scheduling": {{
                                    "config": {{
                                        "startDate": "{d2_iso}",
                                        "timeZoneId": "America/New_York"
                                    }},
                                    "formatted": "{d2_fmt}"
                                }}
                            }}
                        ]
                    }}
                }}
            }}
        }}
    }}
    </script>
    </head>
    <body></body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_warmup_html

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        scraper = BearsDenScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["store_name"] == "The Bear's Den"
    assert result["items_scraped_count"] >= 2
    assert any("Lexi Weege" in d["name"] for d in result["deals"])
    assert any("Karaoke" in d["name"] for d in result["deals"])
    lexi = next(d for d in result["deals"] if "Lexi Weege" in d["name"])
    assert "5 Bank Row, Greenfield, MA" in lexi["description"]
    assert "https://www.thebearsdenbar.com/event-details-1/live-music-lexi-weege" in lexi["description"]
    assert (today_dt + datetime.timedelta(days=1)).strftime("%B") in lexi["price"]


@pytest.mark.asyncio
async def test_bears_den_scrape_fallback():
    """Verify Bears Den scraper produces resilient Greenfield fallbacks on network failure."""
    from app.scrapers.bears_den import BearsDenScraper

    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Network offline")

    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        scraper = BearsDenScraper()
        result = await scraper.scrape(mock_page)

    assert result["kind"] == "event"
    assert result["store_name"] == "The Bear's Den"
    assert result["items_scraped_count"] >= 4
    deal_names = [d["name"] for d in result["deals"]]
    assert any("Karaoke" in n for n in deal_names)
    assert any("Open Mic" in n for n in deal_names)
    assert any("Puzzle" in n for n in deal_names)
    for deal in result["deals"]:
        assert "5 Bank Row, Greenfield, MA" in deal["description"]
        assert "thebearsdenbar.com" in deal["description"]


def test_events_template_renders_bears_den():
    """Verify The Bear's Den renders badge, border, venue card, and event items in events.html."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("events.html")
    today = datetime.date(2026, 10, 8)

    bears_event = {
        "id": 801,
        "store_name": "The Bear's Den",
        "title": "Live Music! Lexi Weege",
        "datetime_label": "October 9, 2026 7:00 PM",
        "description": "Location: The Bear's Den, 5 Bank Row, Greenfield, MA | Lexi Weege live! | Details: https://www.thebearsdenbar.com/event-details-1/live-music-lexi-weege",
        "event_date": datetime.date(2026, 10, 9),
        "detail_url": "https://www.thebearsdenbar.com/event-details-1/live-music-lexi-weege",
    }

    html = template.render(
        has_data=True,
        all_events=[bears_event],
        undated_events=[],
        calendar_events={
            "2026-10-09": [bears_event],
        },
        calendar_weeks=[[datetime.date(2026, 10, 8), datetime.date(2026, 10, 9)]],
        calendar_first_date=today,
        calendar_last_date=today + datetime.timedelta(days=7),
        today=today,
        today_events=[],
        active_store_badges=[
            {
                "name": "The Bear's Den",
                "scraper_key": "bears_den",
                "flyer_url": "https://www.thebearsdenbar.com/event-list",
                "range_label": "Oct 8 - Dec 12",
            }
        ],
    )

    assert "The Bear's Den" in html
    assert "bg-bears-den" in html
    assert "border-bears_den" in html
    assert "5 Bank Row, Greenfield, MA" in html
    assert "https://www.thebearsdenbar.com/event-list" in html
    assert "Live Music! Lexi Weege" in html
    assert "https://www.thebearsdenbar.com/event-details-1/live-music-lexi-weege" in html


def test_events_calendar_always_six_weeks_and_no_undated():
    """Verify calendar view always renders 6 full weeks (42 days) and discards undated events."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models import StoreDataset, StoreDeal
    from app.database import get_db

    today = datetime.date(2026, 11, 15)

    # Create mock dataset with dated and undated deals
    mock_ds = StoreDataset(
        id=9999,
        scraper_key="luthiers_coop",
        store_name="The Luthier's Co-op",
        kind="event",
        status="success",
        expires_at=datetime.datetime(2026, 12, 31, 0, 0, 0),
        deals=[
            StoreDeal(
                id=901,
                item_name="Valid Show",
                sale_price="November 20, 2026 8:00 PM",
                description="Location: Easthampton | Details: https://luthiers.com/1",
            ),
            StoreDeal(
                id=902,
                item_name="Undated Show Without Date",
                sale_price="See venue website",
                description="Location: Easthampton | Details: https://luthiers.com/2",
            ),
        ]
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_ds]
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    with patch("app.store_utils.get_active_event_datasets", return_value=[mock_ds]), \
         patch("app.main.get_active_event_datasets", return_value=[mock_ds]):
        client = TestClient(app)
        response = client.get("/events")
        assert response.status_code == 200
        # Valid show is rendered
        assert "Valid Show" in response.text
        # Undated show without date is excluded
        assert "Undated Show Without Date" not in response.text
        assert "Date not provided by source" not in response.text


@pytest.mark.asyncio
async def test_luthiers_coop_html_tribejson_extraction():
    """Verify Luthiers Co-op scraper extracts events with dates from data-tribejson in HTML."""
    from app.scrapers.luthiers_coop import LuthiersCoopScraper

    mock_html = '''
    <div class="tribe_events type-tribe_events" data-tribejson='{"eventId":"12345-2026-11-20","title":"Deep Trees Live","dateDisplay":"November 20 @ 7:00 pm - 9:00 pm","permalink":"https://www.luthiers-coop.com/event/deep-trees/","excerpt":"Live folk and roots"}' >
        <h3>Deep Trees Live</h3>
    </div>
    <div class="tribe_events type-tribe_events" data-tribejson='{"eventId":"12346-2026-11-21","title":"CLOSED","dateDisplay":"November 21","permalink":"","excerpt":""}' >
        <h3>CLOSED</h3>
    </div>
    '''

    mock_resp_api = MagicMock()
    mock_resp_api.status_code = 404

    mock_resp_html = MagicMock()
    mock_resp_html.status_code = 200
    mock_resp_html.text = mock_html

    async def mock_get(url, *args, **kwargs):
        if "wp-json" in url:
            return mock_resp_api
        return mock_resp_html

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        scraper = LuthiersCoopScraper()
        result = await scraper.scrape()

    assert result["kind"] == "event"
    assert result["items_scraped_count"] >= 1
    assert any("Deep Trees Live" in d["name"] for d in result["deals"])
    deal = next(d for d in result["deals"] if "Deep Trees Live" in d["name"])
    assert "November 20, 2026 7:00 pm - 9:00 pm" in deal["price"]
    assert "https://www.luthiers-coop.com/event/deep-trees/" in deal["description"]
    assert not any(d["name"].upper() == "CLOSED" for d in result["deals"])








