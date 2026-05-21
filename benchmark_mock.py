import time
import random

class Deal:
    def __init__(self, run_id, score, category):
        self.run_id = run_id
        self.score = score
        self.category = category

class MockQuery:
    def __init__(self, data):
        self.data = data

    def filter(self, condition):
        return self

    def order_by(self, field):
        self.data.sort(key=lambda d: d.score if d.score is not None else float('-inf'), reverse=True)
        return self

    def limit(self, num):
        self.data = self.data[:num]
        return self

    def all(self):
        # simulate DB round trip latency
        time.sleep(0.005)
        return self.data.copy()

class MockDB:
    def __init__(self, data):
        self.data = data

    def query(self, model):
        return MockQuery(self.data.copy())

# Generate dummy data
deals_data = [Deal(run_id=1, score=random.randint(0, 100), category=f"cat_{i%10}") for i in range(1000)]
db = MockDB(deals_data)

def old_way():
    # Top 6 deals overall
    top_overall = db.query(Deal).filter(True).order_by(None).limit(6).all()

    # Deals by category
    deals = db.query(Deal).filter(True).all()
    by_cat = {}
    for d in deals:
        if d.category not in by_cat:
            by_cat[d.category] = []
        by_cat[d.category].append(d)
    return top_overall, by_cat

def new_way():
    deals = db.query(Deal).filter(True).all()

    top_overall = sorted(deals, key=lambda d: d.score if d.score is not None else float('-inf'), reverse=True)[:6]

    by_cat = {}
    for d in deals:
        if d.category not in by_cat:
            by_cat[d.category] = []
        by_cat[d.category].append(d)
    return top_overall, by_cat

# Benchmark
import timeit

print("Old way:", timeit.timeit(old_way, number=100))
print("New way:", timeit.timeit(new_way, number=100))
