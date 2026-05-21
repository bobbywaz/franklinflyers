import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Run, Deal
from app.main import read_root

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Create dummy data
run = Run(is_ready=True)
db.add(run)
db.commit()

for i in range(1000):
    db.add(Deal(run_id=run.id, score=i % 100, category=f"cat_{i % 10}"))
db.commit()

# Mock request
from fastapi import Request
class MockRequest:
    def __init__(self):
        self.scope = {"type": "http"}

request = MockRequest()

async def run_benchmark():
    start = time.perf_counter()
    for _ in range(100):
        await read_root(request, db)
    end = time.perf_counter()
    print(f"Time taken: {end - start:.4f} seconds")

import asyncio
asyncio.run(run_benchmark())
