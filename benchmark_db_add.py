import time
from app.database import SessionLocal, init_db
from app.models import Run, GasPrice

def benchmark():
    init_db()
    db = SessionLocal()

    # Generate mock data
    num_items = 1000
    gas_prices = []
    for i in range(num_items):
        gas_prices.append({
            'station_name': f'Station {i}',
            'address': f'{i} Main St',
            'city': 'Springfield',
            'price': 3.50,
            'fuel_type': 'Regular',
            'updated_at': 'Now',
            'source_updated_at': 'Then'
        })

    # Baseline: individual add
    new_run_1 = Run()
    db.add(new_run_1)
    db.commit()
    db.refresh(new_run_1)

    start_time = time.perf_counter()
    for gp in gas_prices:
        db.add(GasPrice(
            run_id=new_run_1.id,
            station_name=gp['station_name'],
            address=gp['address'],
            city=gp['city'],
            price=gp['price'],
            fuel_type=gp['fuel_type'],
            updated_at=gp['updated_at'],
            source_updated_at=gp['source_updated_at']
        ))
    db.commit()
    end_time = time.perf_counter()
    baseline_time = end_time - start_time
    print(f"Baseline (individual add): {baseline_time:.4f} seconds")

    # Optimized: add_all
    new_run_2 = Run()
    db.add(new_run_2)
    db.commit()
    db.refresh(new_run_2)

    start_time = time.perf_counter()
    db.add_all([
        GasPrice(
            run_id=new_run_2.id,
            station_name=gp['station_name'],
            address=gp['address'],
            city=gp['city'],
            price=gp['price'],
            fuel_type=gp['fuel_type'],
            updated_at=gp['updated_at'],
            source_updated_at=gp['source_updated_at']
        ) for gp in gas_prices
    ])
    db.commit()
    end_time = time.perf_counter()
    optimized_time = end_time - start_time
    print(f"Optimized (add_all): {optimized_time:.4f} seconds")

    db.close()

if __name__ == "__main__":
    benchmark()
