from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import Column, Integer, String, ForeignKey

Base = declarative_base()

class Package(Base):
    __tablename__ = 'packages'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    releases = relationship("Release", backref="package", cascade="all, delete-orphan")
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "<Package(name={})>".format(self.name)

class Release(Base):
    __tablename__ = 'releases'
    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey('packages.id'), nullable=False)
    version = Column(String, nullable=False)
    def __init__(self, version):
        self.version = version
    def __repr__(self):
        return "<Release(version={})>".format(self.version)

e = create_engine("sqlite://")
Base.metadata.create_all(e)
Session = sessionmaker(bind=e)
session = Session()

p = Package("foo")
session.add(p)
p.releases = [Release("1"), Release("2"), Release("3")]
session.commit()
print(p, p.releases)
session.delete(p.releases[1])
r = Release("12")
r.package = p
session.add(r)
session.commit()
print(p, p.releases)

pp1 = Package("test1")
pp2 = session.query(Package).filter_by(name="foo").first()
pp3 = session.query(Package).filter_by(name="bar").first()
print(pp1, pp2, pp3)
pp1.name = 'pp1'
pp2.name = 'pp2'
# pp3 is None because nothing was found...
# pp3.name = 'pp3'

# Prints pp2 because session.query adds objects to the session
print(session.dirty)
