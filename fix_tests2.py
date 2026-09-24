with open("tests/test_dispensaries.py", "r") as f:
    content = f.read()
content = content.replace(
    '    client = TestClient(app)\n    response = client.get("/dispensaries")',
    '    from unittest.mock import patch, MagicMock\n    with patch("app.main.get_active_dispensary_datasets") as mock_get:\n        mock_dataset = MagicMock()\n        mock_dataset.store_name = "Patriot Care"\n        mock_deal = MagicMock()\n        mock_deal.item_name = "Weed"\n        mock_deal.description = "BOGO Free"\n        mock_deal.sale_price = "$10"\n        mock_dataset.deals = [mock_deal]\n        mock_get.return_value = [mock_dataset]\n        client = TestClient(app)\n        response = client.get("/dispensaries")'
)
with open("tests/test_dispensaries.py", "w") as f:
    f.write(content)

with open("tests/test_home.py", "r") as f:
    content = f.read()
if "import app.main" not in content:
    content = content.replace("from starlette.testclient import TestClient", "from starlette.testclient import TestClient\nimport app.main")
content = content.replace(
    '    client = TestClient(app)\n    response = client.get("/")',
    '    from unittest.mock import patch, MagicMock\n    with patch("app.main.get_active_grocery_datasets") as mock_get:\n        mock_dataset = MagicMock()\n        mock_dataset.store_name = "ALDI"\n        mock_dataset.scraper_key = "aldi"\n        mock_dataset.flyer_start_date = None\n        mock_dataset.flyer_end_date = None\n        mock_get.return_value = [mock_dataset]\n        client = TestClient(app)\n        response = client.get("/")'
)
with open("tests/test_home.py", "w") as f:
    f.write(content)

with open("tests/test_movies.py", "r") as f:
    content = f.read()
if "from unittest.mock import patch" not in content:
    content = content.replace("import pytest", "import pytest\nfrom unittest.mock import patch, MagicMock")
content = content.replace(
    '        movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=2.5, max_movies=8, now_ref=ref_time)',
    '        mock_dataset = MagicMock()\n        mock_dataset.flyer_start_date = datetime.datetime.now().date()\n        mock_movie = MagicMock()\n        mock_movie.item_name = "Test Movie"\n        mock_movie.description = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S-04:00")\n        mock_movie.score = 5\n        mock_dataset.deals = [mock_movie]\n        with patch("app.main.get_active_movie_datasets", return_value=[mock_dataset]):\n            movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=2.5, max_movies=8, now_ref=ref_time)'
)
with open("tests/test_movies.py", "w") as f:
    f.write(content)

with open("tests/test_pharmacies.py", "r") as f:
    content = f.read()
content = content.replace(
    '    client = TestClient(app)\n    response = client.get("/pharmacies")',
    '    from unittest.mock import patch, MagicMock\n    with patch("app.main.get_active_pharmacy_datasets") as mock_get:\n        mock_dataset = MagicMock()\n        mock_dataset.store_name = "CVS"\n        mock_dataset.scraper_key = "cvs_greenfield"\n        mock_deal = MagicMock()\n        mock_deal.item_name = "Vitamin C"\n        mock_deal.description = "BOGO Free"\n        mock_deal.sale_price = "$10"\n        mock_dataset.deals = [mock_deal]\n        mock_get.return_value = [mock_dataset]\n        client = TestClient(app)\n        response = client.get("/pharmacies")'
)
with open("tests/test_pharmacies.py", "w") as f:
    f.write(content)
