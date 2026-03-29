import timeit
import collections

class DealMock:
    def __init__(self, category):
        self.category = category

# Mock data
import random
random.seed(42)
categories = ['Meat', 'Produce', 'Dairy', 'Snacks', 'Beverages', 'Bakery', 'Frozen', 'Pantry']
deals = [DealMock(random.choice(categories)) for _ in range(1000)]

def method_original():
    by_cat = {}
    for d in deals:
        if d.category not in by_cat:
            by_cat[d.category] = []
        by_cat[d.category].append(d)
    return by_cat

def method_defaultdict():
    by_cat = collections.defaultdict(list)
    for d in deals:
        by_cat[d.category].append(d)
    return by_cat

# Run benchmark
n = 10000
time_original = timeit.timeit(method_original, number=n)
time_defaultdict = timeit.timeit(method_defaultdict, number=n)

print(f"Original method: {time_original:.5f}s")
print(f"Defaultdict method: {time_defaultdict:.5f}s")
if time_original > 0:
    improvement = ((time_original - time_defaultdict) / time_original) * 100
    print(f"Improvement: {improvement:.2f}%")
