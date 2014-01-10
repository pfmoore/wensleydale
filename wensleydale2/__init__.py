from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, and_
from sqlalchemy.schema import Table
from xmlrpc.client import ServerProxy
import json
from .model import Base, Package, Release, new_package, new_release

# ===========================================================
#
# from progressbar import ProgressBar, Bar, Percentage, ETA
# def pb(name):
#     return [name, ': ', Percentage(), ' ', Bar(), ' ', ETA()]
#
# ===========================================================

class PYPISource:
    PYPI_URL = 'http://pypi.python.org/pypi'
    def __init__(self):
        self.pypi = ServerProxy(self.PYPI_URL)
    def packages(self):
        return self.pypi.list_packages()
    def releases(self, package):
        return self.pypi.package_releases(package, True)
    def urls(self, package, version):
        return self.pypi.release_urls(package, version)
    def release_data(self, package, version):
        return self.pypi.release_data(package, version)

class JSONSource:
    def __init__(self, url='sqlite:///pypi.db'):
        engine = create_engine(url)
        meta = MetaData(engine)
        self.packages_t = Table('packages', meta, autoload=True)
        self.releases_t = Table('releases', meta, autoload=True)
    def packages(self):
        sel = select([self.packages_t.c.package])
        rs = sel.execute()
        return [r[0] for r in rs]
    def releases(self, package):
        sel = select([self.releases_t.c.version]).where(self.releases_t.c.package == package)
        rs = sel.execute()
        return [r[0] for r in rs]
    def urls(self, package, version):
        sel = select([self.releases_t.c.json]).where(and_(
            (self.releases_t.c.package == package),
            (self.releases_t.c.version == version)
        ))
        j = sel.scalar()
        try:
            data = json.loads(j)
        except ValueError:
            return []
        return data['urls']
    def release_data(self, package, version):
        sel = select([self.releases_t.c.json]).where(and_(
            (self.releases_t.c.package == package),
            (self.releases_t.c.version == version)
        ))
        j = sel.scalar()
        try:
            data = json.loads(j)
        except ValueError:
            return {}
        return data['info']
    def release_data_and_urls(self, package, version):
        sel = select([self.releases_t.c.json]).where(and_(
            (self.releases_t.c.package == package),
            (self.releases_t.c.version == version)
        ))
        j = sel.scalar()
        try:
            data = json.loads(j)
        except ValueError:
            return ({}, [])
        return data['info'], data['urls']

def load_release(session, src, pkg, ver):
    d, u = src.release_data_and_urls(pkg, ver)
    if not d:
        return False
    r = new_release(pkg, ver, d, u)
    session.merge(r)
    return True

def load_package(session, src, pkg):
    rels = src.releases(pkg)
    print("{} ({} versions): ".format(pkg, len(rels)), end='', flush=True)
    p = new_package(pkg, rels)
    session.merge(p)
    for ver in rels:
        ok = load_release(session, src, pkg, ver)
        print("." if ok else "X", end="", flush=True)
    print(" OK")

def init(db):
    Base.metadata.create_all(db)

def rename(db, pkg_old, pkg_new):
    Session = sessionmaker(bind=db)
    session = Session()
    pkg = session.query(Package).filter_by(name=pkg_old).first()
    pkg.name = pkg_new
    session.commit()

def remove(db, pkg, ver=None):
    Session = sessionmaker(bind=db)
    session = Session()
    if ver:
        obj = session.query(Release).join(Package).filter(Package.name == pkg).filter(Release.version == ver).first()
    else:
        obj = session.query(Package).filter_by(name=pkg).first()
    session.delete(obj)
    session.commit()

def get(src, db, pkg, ver=None):
    Session = sessionmaker(bind=db)
    session = Session()
    if ver:
        d, u = src.release_data_and_urls(pkg, ver)
        if not d:
            return
        with session.no_autoflush:
            rel = new_release(pkg, ver, d, u)
        session.merge(rel)
    else:
        load_package(session, src, pkg)
    session.commit()

def main():
    e = create_engine("sqlite:///t.db")
    Base.metadata.create_all(e)
    Session = sessionmaker(bind=e)

    src = JSONSource()
    session = Session()
    #bar = ProgressBar(widgets=pb("Packages"))

    for pkg in src.packages()[:100000]:
        load_package(session, src, pkg)
    session.commit()

