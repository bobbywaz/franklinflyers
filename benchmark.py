import timeit

setup_list = """
valid_categories = [
    "Produce", "Meat and Seafood", "Deli", "Beverages",
    "Pantry", "Dairy", "Canned Goods", "Frozen", "Household"
]
items = ["Produce", "Dairy", "Unknown", "Pantry", "Not a category", "Household"] * 20
"""

setup_set = """
valid_categories = {
    "Produce", "Meat and Seafood", "Deli", "Beverages",
    "Pantry", "Dairy", "Canned Goods", "Frozen", "Household"
}
items = ["Produce", "Dairy", "Unknown", "Pantry", "Not a category", "Household"] * 20
"""

test_code = """
for item in items:
    _ = item in valid_categories
"""

list_time = timeit.timeit(test_code, setup=setup_list, number=10000)
set_time = timeit.timeit(test_code, setup=setup_set, number=10000)

print(f"List time: {list_time:.6f} seconds")
print(f"Set time:  {set_time:.6f} seconds")
print(f"Improvement: {(list_time - set_time) / list_time * 100:.2f}% faster")
