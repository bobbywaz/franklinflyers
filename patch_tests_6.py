import re

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_str, new_str)
    with open(file_path, "w") as f:
        f.write(content)

replace_in_file("tests/test_dispensaries.py", "kind=\"dispensary\",", "kind=\"dispensary\", trigger_mode=\"manual\",")
replace_in_file("tests/test_home.py", "kind=\"grocery\",", "kind=\"grocery\", trigger_mode=\"manual\",")
replace_in_file("tests/test_pharmacies.py", "kind=\"pharmacy\",", "kind=\"pharmacy\", trigger_mode=\"manual\",")
replace_in_file("tests/test_movies.py", "kind=\"movie\",", "kind=\"movie\", trigger_mode=\"manual\",")
