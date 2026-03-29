import time
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from app.models import Base, Run, Deal, BestStore, FailedScrape
from app.database import engine, SessionLocal
import os

def setup_db():
    if os.path.exists("./franklin_flyers.db"):
        os.remove("./franklin_flyers.db")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    for i in range(10):
        run = Run()
        db.add(run)
        db.commit()
        db.refresh(run)

        fs1 = FailedScrape(run_id=run.id, store_name="Store A", error_message="Error")
        fs2 = FailedScrape(run_id=run.id, store_name="Store B", error_message="Error")
        bs = BestStore(run_id=run.id, store_name="Store C", summary="Great", strengths="Cheap", weaknesses="Far", score=10)

        db.add_all([fs1, fs2, bs])

        for j in range(20):
            d = Deal(run_id=run.id, store_name="Store C", item_name=f"Item {j}", sale_price="$1.00", category="Produce", score=9)
            db.add(d)

    db.commit()
    db.close()

def run_benchmark(eager):
    db = SessionLocal()

    query_count = [0]

    @event.listens_for(engine, 'before_cursor_execute')
    def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
        query_count[0] += 1

    start = time.time()

    if eager:
        from sqlalchemy.orm import joinedload
        latest_run = db.query(Run).options(
            joinedload(Run.failed_scrapes),
            joinedload(Run.best_store)
        ).order_by(Run.run_date.desc()).first()
    else:
        latest_run = db.query(Run).order_by(Run.run_date.desc()).first()

    if latest_run:
        failed_scrapes = latest_run.failed_scrapes
        best_store = latest_run.best_store

    end = time.time()

    event.remove(engine, 'before_cursor_execute', receive_before_cursor_execute)
    db.close()

    return query_count[0], end - start

if __name__ == "__main__":
    setup_db()

    # Warmup
    run_benchmark(False)
    run_benchmark(True)

    count_lazy, time_lazy = run_benchmark(False)
    count_eager, time_eager = run_benchmark(True)

    print(f"Lazy loading: {count_lazy} queries, {time_lazy:.6f} seconds")
    print(f"Eager loading: {count_eager} queries, {time_eager:.6f} seconds")
