from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .model import Base

class DB:
    def __init__(self, engine="sqlite://"):
        self.engine = create_engine(engine)
        self.Session = sessionmaker(bind=self.engine)
    def create_schema(self):
        Base.metadata.create_all(self.engine)
    def session(self):
        return self.Session()
