import time
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class GasPrice(Base):
    __tablename__ = 'gas_prices'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer)
    station_name = Column(String)
    address = Column(String)
    city = Column(String)
    price = Column(Float)
    fuel_type = Column(String)
    updated_at = Column(DateTime)
    source_updated_at = Column(DateTime)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def baseline_benchmark(num_items=1000):
    session = Session()
    gas_prices_data = [
        {
            'station_name': f'Station {i}',
            'address': f'12{i} Main St',
            'city': 'Test City',
            'price': 3.50 + (i % 10) * 0.1,
            'fuel_type': 'Regular',
            'updated_at': None,
            'source_updated_at': None
        } for i in range(num_items)
    ]

    start_time = time.time()
    for gp in gas_prices_data:
        session.add(GasPrice(
            run_id=1,
            station_name=gp['station_name'],
            address=gp['address'],
            city=gp['city'],
            price=gp['price'],
            fuel_type=gp['fuel_type'],
            updated_at=gp['updated_at'],
            source_updated_at=gp['source_updated_at']
        ))
    session.commit()
    end_time = time.time()

    return end_time - start_time

def optimized_benchmark_bulk_save(num_items=1000):
    session = Session()
    gas_prices_data = [
        {
            'station_name': f'Station {i}',
            'address': f'12{i} Main St',
            'city': 'Test City',
            'price': 3.50 + (i % 10) * 0.1,
            'fuel_type': 'Regular',
            'updated_at': None,
            'source_updated_at': None
        } for i in range(num_items)
    ]

    start_time = time.time()
    objects = [GasPrice(
            run_id=1,
            station_name=gp['station_name'],
            address=gp['address'],
            city=gp['city'],
            price=gp['price'],
            fuel_type=gp['fuel_type'],
            updated_at=gp['updated_at'],
            source_updated_at=gp['source_updated_at']
        ) for gp in gas_prices_data]
    session.bulk_save_objects(objects)
    session.commit()
    end_time = time.time()

    return end_time - start_time

print(f"Baseline (1000 items): {baseline_benchmark()} seconds")
print(f"Optimized bulk_save (1000 items): {optimized_benchmark_bulk_save()} seconds")

print(f"Baseline (10000 items): {baseline_benchmark(10000)} seconds")
print(f"Optimized bulk_save (10000 items): {optimized_benchmark_bulk_save(10000)} seconds")
