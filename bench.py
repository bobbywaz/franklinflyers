import time
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class GasPrice(Base):
    __tablename__ = 'gas_prices'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer)
    station_name = Column(String)
    address = Column(String)
    city = Column(String)
    price = Column(String)
    fuel_type = Column(String)
    updated_at = Column(String)
    source_updated_at = Column(String)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def bench_add():
    session = Session()
    start = time.time()
    for i in range(10000):
        session.add(GasPrice(run_id=1, station_name="A", address="B", city="C", price="D", fuel_type="E", updated_at="F", source_updated_at="G"))
    session.commit()
    return time.time() - start

def bench_add_all():
    session = Session()
    start = time.time()
    objects = [GasPrice(run_id=1, station_name="A", address="B", city="C", price="D", fuel_type="E", updated_at="F", source_updated_at="G") for i in range(10000)]
    session.add_all(objects)
    session.commit()
    return time.time() - start

def bench_bulk_save():
    session = Session()
    start = time.time()
    objects = [GasPrice(run_id=1, station_name="A", address="B", city="C", price="D", fuel_type="E", updated_at="F", source_updated_at="G") for i in range(10000)]
    session.bulk_save_objects(objects)
    session.commit()
    return time.time() - start

print(f"add: {bench_add()}")
print(f"add_all: {bench_add_all()}")
print(f"bulk_save: {bench_bulk_save()}")
