from app.database import Base, engine

def pytest_configure():
    Base.metadata.create_all(bind=engine)
