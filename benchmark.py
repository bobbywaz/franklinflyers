import time
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class Deal(Base):
    __tablename__ = 'deals'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer)
    store_name = Column(String(50))
    item_name = Column(String(100))
    description = Column(String(200))
    sale_price = Column(String(20))
    category = Column(String(50))
    score = Column(Integer)
    explanation = Column(Text)

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def generate_deals(n):
    return [{
        'store_name': f"Store {i}",
        'item_name': f"Item {i}",
        'size': "1 lb",
        'sale_price': f"${i}",
        'category': 'Produce',
        'score': 90,
        'explanation': 'Good deal'
    } for i in range(n)]

def benchmark_individual(deals, run_id):
    db = SessionLocal()
    start = time.time()
    for d in deals:
        db.add(Deal(
            run_id=run_id,
            store_name=d['store_name'],
            item_name=d['item_name'],
            description=d.get('size', ''),
            sale_price=d['sale_price'],
            category=d['category'],
            score=d['score'],
            explanation=d['explanation']
        ))
    db.commit()
    duration = time.time() - start
    db.close()
    return duration

def benchmark_bulk(deals, run_id):
    db = SessionLocal()
    start = time.time()
    db.add_all([Deal(
        run_id=run_id,
        store_name=d['store_name'],
        item_name=d['item_name'],
        description=d.get('size', ''),
        sale_price=d['sale_price'],
        category=d['category'],
        score=d['score'],
        explanation=d['explanation']
    ) for d in deals])
    db.commit()
    duration = time.time() - start
    db.close()
    return duration

print("Warming up...")
deals = generate_deals(1000)
benchmark_individual(deals, 1)
benchmark_bulk(deals, 2)

print("Running benchmark...")
deals = generate_deals(5000)
t1 = benchmark_individual(deals, 3)
t2 = benchmark_bulk(deals, 4)
print(f"Individual adds (5000 items): {t1:.4f}s")
print(f"Bulk adds (5000 items): {t2:.4f}s")
print(f"Improvement: {(t1-t2)/t1*100:.2f}%")
