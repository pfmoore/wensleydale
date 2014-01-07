from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String

Base = declarative_base()

class Person(Base):
  __tablename__ = 'person'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  phone = Column(String)
  def __repr__(self):
    return "<Person(name={})>".format(self.name)

e = create_engine("sqlite://")
Base.metadata.create_all(e)
Session = sessionmaker(bind=e)

p = Person()
#p.name="Gustav Enk"

s = Session()
s.add(p)
print(s.query(Person).all())
print(list(e.execute("select * from person")))
