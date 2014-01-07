from sqlalchemy import Table, Column, Boolean, Integer, String, DateTime, MetaData
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Package(Base):
    __tablename__ = "packages"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
