import re

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_str, new_str)
    with open(file_path, "w") as f:
        f.write(content)

replace_in_file("tests/test_dispensaries.py", "created_at=utcnow()", "")
replace_in_file("tests/test_home.py", "created_at=utcnow()", "")
replace_in_file("tests/test_pharmacies.py", "created_at=utcnow()", "")
replace_in_file("tests/test_movies.py", "created_at=utcnow()", "")
