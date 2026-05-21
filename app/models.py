from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Run(Base):
    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_ready = Column(Boolean, default=False)
    seasonal_info = Column(Text) # JSON string containing in_season and out_season
    recipe_idea = Column(Text) # JSON string containing recipe details
    
    deals = relationship("Deal", back_populates="run")
    gas_prices = relationship("GasPrice", back_populates="run")
    best_store = relationship("BestStore", uselist=False, back_populates="run")
    failed_scrapes = relationship("FailedScrape", back_populates="run")
    published_stores = relationship("PublishedSnapshotStore", back_populates="run")

class Deal(Base):
    __tablename__ = 'deals'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    store_name = Column(String)
    item_name = Column(String)
    sale_price = Column(String)
    description = Column(String)
    category = Column(String)
    score = Column(Integer)
    explanation = Column(Text)
    
    run = relationship("Run", back_populates="deals")

class BestStore(Base):
    __tablename__ = 'best_stores'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    store_name = Column(String)
    summary = Column(Text)
    strengths = Column(Text)
    weaknesses = Column(Text)
    score = Column(Integer)

    run = relationship("Run", back_populates="best_store")

class GasPrice(Base):
    __tablename__ = 'gas_prices'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    station_name = Column(String)
    address = Column(String)
    city = Column(String)
    price = Column(String)
    fuel_type = Column(String)
    updated_at = Column(String)
    source_updated_at = Column(String)
    
    run = relationship("Run", back_populates="gas_prices")

class FailedScrape(Base):
    __tablename__ = 'failed_scrapes'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    store_name = Column(String)
    error_message = Column(Text)

    run = relationship("Run", back_populates="failed_scrapes")

class StoreDataset(Base):
    __tablename__ = 'store_datasets'
    id = Column(Integer, primary_key=True)
    scraper_key = Column(String, index=True, nullable=False)
    store_name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # grocery or gas
    trigger_mode = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success or failed
    started_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    flyer_start_date = Column(Date)
    flyer_end_date = Column(Date)
    expires_at = Column(DateTime)
    next_refresh_at = Column(DateTime)
    date_source = Column(String)
    item_count = Column(Integer, default=0)
    items_scraped_count = Column(Integer, default=0)
    error_message = Column(Text)

    deals = relationship("StoreDeal", back_populates="dataset", cascade="all, delete-orphan")
    gas_prices = relationship("StoreGasPrice", back_populates="dataset", cascade="all, delete-orphan")
    published_entries = relationship("PublishedSnapshotStore", back_populates="dataset")

class StoreDeal(Base):
    __tablename__ = 'store_deals'
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey('store_datasets.id'), nullable=False)
    item_name = Column(String)
    sale_price = Column(String)
    description = Column(String)

    dataset = relationship("StoreDataset", back_populates="deals")

class StoreGasPrice(Base):
    __tablename__ = 'store_gas_prices'
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey('store_datasets.id'), nullable=False)
    station_name = Column(String)
    address = Column(String)
    city = Column(String)
    price = Column(String)
    fuel_type = Column(String)
    updated_at = Column(String)
    source_updated_at = Column(String)

    dataset = relationship("StoreDataset", back_populates="gas_prices")

class PublishedSnapshotStore(Base):
    __tablename__ = 'published_snapshot_stores'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'), nullable=False)
    store_dataset_id = Column(Integer, ForeignKey('store_datasets.id'))
    scraper_key = Column(String, nullable=False)
    store_name = Column(String, nullable=False)

    run = relationship("Run", back_populates="published_stores")
    dataset = relationship("StoreDataset", back_populates="published_entries")
    
class Configuration(Base):
    __tablename__ = 'configurations'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)
