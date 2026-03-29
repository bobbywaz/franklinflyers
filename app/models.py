from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Run(Base):
    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    run_date = Column(DateTime, default=datetime.datetime.utcnow)
    seasonal_info = Column(Text) # JSON string containing in_season and out_season
    recipe_idea = Column(Text) # JSON string containing recipe details
    
    deals = relationship("Deal", back_populates="run")
    gas_prices = relationship("GasPrice", back_populates="run")
    best_store = relationship("BestStore", uselist=False, back_populates="run")
    failed_scrapes = relationship("FailedScrape", back_populates="run")

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

class FailedScrape(Base):
    __tablename__ = 'failed_scrapes'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    store_name = Column(String)
    error_message = Column(Text)

    run = relationship("Run", back_populates="failed_scrapes")

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
    
    run = relationship("Run", back_populates="gas_prices")
