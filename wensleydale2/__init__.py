from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import select, and_
from sqlalchemy.schema import Table
from xmlrpc.client import ServerProxy
import json
import datetime
from .model import Base, Package, Release, URL, new_package, set_release_data

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

# Actions
# =======

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

# The following is messy (and wrong)
#
# What we want are the following actions:
#
# 1. Load a completely new package
# 1a. Update a package (can be implemented as delete & load).
#     Having update as separate may offer opportunities for optimisation, but
#     it's not clear at the moment if that would acrtually be true.
# 2. Add a release to a package

def new(src, db, pkg):
    Session = sessionmaker(bind=db)
    session = Session()
    
    # Error checking - handle a package that exists already
    package = Package(pkg)
    session.add(package)
    package.releases = [Release(ver) for ver in src.releases(pkg)]

    for rel in package.releases:
        data, urls = src.release_data_and_urls(pkg, rel.version)
        set_release_data(rel, data, urls)

    session.commit()

def new_rel(src, db, pkg, ver):
    Session = sessionmaker(bind=db)
    session = Session()
    
    # Package must exist! Error checking...
    package = session.query(Package).filter(Package.name == pkg).first()
    release = Release(ver)
    data, urls = src.release_data_and_urls(pkg, ver)
    set_release_data(release, data, urls)
    release.package = package

    session.commit()

def get(src, db, pkg, ver=None):
    Session = sessionmaker(bind=db)
    session = Session()

    # Find the package. If there isn't one already, create it
    package = session.query(Package).filter(Package.name == pkg).first()
    if package is None:
        package = Package(pkg)
    # Add the package to the sesion, as we're changing its list of releases
    session.add(package)
    # If we are getting a specific version, first delete it if it's already
    # present (this will remove it from the package's list of releases)
    if ver:
        rel = session.query(Release).join(Package).filter(Package.name == pkg).filter(Release.version == ver).first()
        if rel:
            print(">>> DELETING", rel.version, rel.package_id)
            # Doesn't work because it's still in the package's list...
            session.delete(rel)
        versions = [ver]
    else:
        # We are refreshing all releases, so get the list of releases and
        # clear the existing releases from the package object.
        versions = src.releases(pkg)
        package.releases = []

    # Create a new release object for each version, and set its package. This
    # will add it to the package's list of releases.
    for v in versions:
        d, u = src.release_data_and_urls(pkg, v)
        if not d:
            return
        rel = Release(v)
        set_release_data(rel, d, u)
        rel.package = package
    session.commit()

def process_change(src, db, change):
    pkg, ver, timestamp, action, serial = change
    ts = datetime.datetime(1070,1,1) + datetime.timedelta(seconds=timestamp)
    act = action.split()

    if act[0] == 'remove' and len(act) == 1:
        remove(db, pkg, ver)
    elif act[0] == 'new' and act[1] == 'release' and len(act) == 2:
        new_rel(src, db, pkg, ver)
    elif act[0] == 'rename' and act[1] == 'from' and len(act) == 3:
        rename(db, act[2], pkg)
    elif act[0] == 'add' and len(act) > 2 and (act[2] == 'url' or act[3] == 'file'):
        update(src, db, pkg, ver)
    elif act[0] == 'update' and ver:
        update(src, db, pkg, ver)
    elif act[0] == 'update' and act[1] == 'hosting_mode':
        pass
    elif (act[0] == 'remove' or act[0] == 'new') and (act[1] == 'Owner' or act[1] == 'Maintainer'):
        pass # Nothing to do
    else:
        print("Unknown action: {} for {}{}".format(action, pkg,  '/' + ver if ver else ""))

def main():
    e = create_engine("sqlite:///t.db")
    Base.metadata.create_all(e)
    Session = sessionmaker(bind=e)

    src = JSONSource()

    for pkg in src.packages()[:100000]:
        get(e, src, pkg)

