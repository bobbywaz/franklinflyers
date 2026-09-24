import re

def fix_file(filepath, search, replace):
    with open(filepath, "r") as f:
        content = f.read()
    content = content.replace(search, replace)
    with open(filepath, "w") as f:
        f.write(content)

fix_file("tests/test_dispensaries.py",
"""    client = TestClient(app)
    response = client.get("/dispensaries")""",
"""    from unittest.mock import patch, MagicMock
    with patch("app.main.get_active_dispensary_datasets") as mock_get:
        mock_dataset = MagicMock()
        mock_dataset.store_name = "Patriot Care"
        mock_deal = MagicMock()
        mock_deal.item_name = "Weed"
        mock_deal.description = "BOGO Free"
        mock_deal.sale_price = "$10"
        mock_dataset.deals = [mock_deal]
        mock_get.return_value = [mock_dataset]
        client = TestClient(app)
        response = client.get("/dispensaries")""")

fix_file("tests/test_home.py",
"""    client = TestClient(app)
    response = client.get("/")""",
"""    from unittest.mock import patch, MagicMock
    with patch("app.main.get_active_grocery_datasets") as mock_get:
        mock_dataset = MagicMock()
        mock_dataset.store_name = "ALDI"
        mock_dataset.scraper_key = "aldi"
        mock_dataset.flyer_start_date = None
        mock_dataset.flyer_end_date = None
        mock_get.return_value = [mock_dataset]
        client = TestClient(app)
        response = client.get("/")""")

fix_file("tests/test_movies.py",
"""        movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=2.5, max_movies=8, now_ref=ref_time)""",
"""        from unittest.mock import patch, MagicMock
        mock_dataset = MagicMock()
        mock_dataset.flyer_start_date = datetime.datetime.now().date()
        mock_movie = MagicMock()
        mock_movie.item_name = "Test Movie"
        mock_movie.description = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S-04:00")
        mock_movie.score = 5
        mock_dataset.deals = [mock_movie]
        with patch("app.main.get_active_movie_datasets", return_value=[mock_dataset]):
            movies = _get_upcoming_wheel_movies(db, today=ref_time.date(), max_hours_ahead=2.5, max_movies=8, now_ref=ref_time)""")

fix_file("tests/test_pharmacies.py",
"""    client = TestClient(app)
    response = client.get("/pharmacies")""",
"""    from unittest.mock import patch, MagicMock
    with patch("app.main.get_active_pharmacy_datasets") as mock_get:
        mock_dataset = MagicMock()
        mock_dataset.store_name = "CVS"
        mock_dataset.scraper_key = "cvs_greenfield"
        mock_deal = MagicMock()
        mock_deal.item_name = "Vitamin C"
        mock_deal.description = "BOGO Free"
        mock_deal.sale_price = "$10"
        mock_dataset.deals = [mock_deal]
        mock_get.return_value = [mock_dataset]
        client = TestClient(app)
        response = client.get("/pharmacies")""")
