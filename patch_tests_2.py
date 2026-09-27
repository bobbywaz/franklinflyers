import re

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_str, new_str)
    with open(file_path, "w") as f:
        f.write(content)

replace_in_file("tests/test_dispensaries.py", "store_type=\"dispensary\",", "kind=\"dispensary\",")
replace_in_file("tests/test_home.py", "store_type=\"grocery\",", "kind=\"grocery\",")
replace_in_file("tests/test_pharmacies.py", "store_type=\"pharmacy\",", "kind=\"pharmacy\",")
replace_in_file("tests/test_movies.py", "store_type=\"movie\",", "kind=\"movie\",")
