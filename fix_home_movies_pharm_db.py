from datetime import timedelta
import re

# 1. test_home.py (Add Deal to Run)
with open("tests/test_home.py", "r") as f:
    content = f.read()

home_deal = """
    from app.models import Deal
    deal_run = Deal(run_id=run.id, store_name="ALDI", item_name="Milk", sale_price="$2.00", description="Good", category="Dairy", score=10)
    db.add(deal_run)
"""
content = content.replace('run = Run(run_date=now, is_ready=True)\n    db.add(run)\n    db.commit()', 'run = Run(run_date=now, is_ready=True)\n    db.add(run)\n    db.commit()' + home_deal)
with open("tests/test_home.py", "w") as f:
    f.write(content)

# 2. test_movies.py (Fix time)
with open("tests/test_movies.py", "r") as f:
    content = f.read()

movie_time_fix = """
    import zoneinfo
    import datetime as dt
    tz = zoneinfo.ZoneInfo("America/New_York")
    ref_time = dt.datetime.combine(now.date(), dt.time(16, 15), tzinfo=tz)
    deal2 = StoreDeal(dataset_id=ds.id, item_name="Upcoming Movie", sale_price="PG-13", description=(ref_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S-04:00"))
"""
content = re.sub(r'    deal2 = StoreDeal\(dataset_id=ds.id, item_name="Upcoming Movie".*?\n', movie_time_fix, content)
with open("tests/test_movies.py", "w") as f:
    f.write(content)
