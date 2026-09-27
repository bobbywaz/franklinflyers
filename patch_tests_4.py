import re

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_str, new_str)
    with open(file_path, "w") as f:
        f.write(content)

replace_in_file("tests/test_dispensaries.py", "kind=\"dispensary\",", "kind=\"dispensary\", scraper_key=\"patriot_care\",")
replace_in_file("tests/test_home.py", "kind=\"grocery\",", "kind=\"grocery\", scraper_key=\"big_y\",")
replace_in_file("tests/test_pharmacies.py", "kind=\"pharmacy\",", "kind=\"pharmacy\", scraper_key=\"cvs_greenfield\",")
replace_in_file("tests/test_movies.py", "kind=\"movie\",", "kind=\"movie\", scraper_key=\"cinemark_hadley\",")
