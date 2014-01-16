from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select, and_
from sqlalchemy.schema import Table
from xmlrpc.client import ServerProxy
import json
import datetime
from .model import Base, LatestChange, Package, Release, URL, new_package, set_release_data

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
    def release_data_and_urls(self, package, version):
        return [self.release_data(package, version), self.urls(package, version)]
    def latest(self):
        return self.pypi.changelog_last_serial()
    def changes(self, serial):
        return self.pypi.changelog_since_serial(serial)

class JSONSource:
    def __init__(self, url='sqlite:///pypi.db'):
        engine = create_engine(url)
        meta = MetaData(engine)
        self.serial_t = Table('last_serial', meta, autoload=True)
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
    def latest(self):
        sel = select([self.serial_t.c.latest])
        rs = sel.execute()
        return rs[0][0]
    def changes(self, serial):
        return []

# Actions
# =======

def init(db):
    Base.metadata.create_all(db)

def pkg_rename(session, old, new, serial=0):
    pkg = session.query(Package).filter_by(name=old).first()
    pkg.name = new
    pkg.serial = serial

def pkg_remove(session, name):
    pkg = session.query(Package).filter_by(name=name).first()
    if pkg:
        session.delete(pkg)
    else:
        pass # print("Failed to remove {}".format(name))

def rel_remove(session, name, ver):
    rel = session.query(Release).join(Package).filter(Package.name == name).filter(Release.version == ver).first()
    if rel:
        session.delete(rel)
    else:
        pass # print("Failed to remove {}/{}".format(name, ver))

def pkg_add(session, src, name, serial=0):
    # Error checking - handle a package that exists already
    pkg = Package(name)
    session.add(pkg)
    pkg.serial = serial
    pkg.releases = [Release(ver) for ver in src.releases(name)]

    for rel in pkg.releases:
        data, urls = src.release_data_and_urls(name, rel.version)
        set_release_data(rel, data, urls)

def rel_add(session, src, name, ver, serial=0):
    # Package must exist! Error checking...
    pkg = session.query(Package).filter(Package.name == name).first()
    if not pkg:
        return
    for r in pkg.releases:
        if r.version == ver:
            session.delete(r)
            break
    release = Release(ver)
    data, urls = src.release_data_and_urls(name, ver)
    set_release_data(release, data, urls)
    release.package = pkg
    release.serial = serial

def process_change(src, session, change):
    name, ver, timestamp, action, serial = change
    ts = datetime.datetime(1070,1,1) + datetime.timedelta(seconds=timestamp)
    act = action.split()

    if len(act) == 1 and act[0] == 'create':
        pkg_remove(session, name)
        session.flush()
        pkg_add(session, src, name)
    elif len(act) == 1 and act[0] == 'remove':
        rel_remove(session, name, ver)
    elif len(act) == 2 and act[0] == 'new' and act[1] == 'release':
        rel_remove(session, name, ver) # defensive...
        rel_add(session, src, name, ver, serial)
    elif len(act) == 3 and act[0] == 'rename' and act[1] == 'from':
        pkg_rename(session, act[2], name, serial)
    elif len(act) > 2 and act[0] == 'add' and (act[1] == 'url' or act[2] == 'file'):
        rel_remove(session, name, ver)
        rel_add(session, src, name, ver, serial)
    elif len(act) > 0 and act[0] == 'update' and ver:
        rel_remove(session, name, ver)
        rel_add(session, src, name, ver, serial)
    elif len(act) > 0 and act[0] == 'docupdate':
        pass # Possibly wrong...
    elif len(act) > 1 and act[0] == 'update' and act[1] == 'hosting_mode':
        pass
    elif len(act) > 1 and act[0] == 'remove' and act[1] == 'file':
        rel_remove(session, name, ver)
        rel_add(session, src, name, ver, serial)
    elif len(act) > 1 and (act[0] == 'remove' or act[0] == 'add') and (act[1] == 'Owner' or act[1] == 'Maintainer'):
        pass # Nothing to do
    else:
        print("Unknown action: {} for {}{}".format(action, name,  '/' + ver if ver else ""))

    set_latest(session, serial)

def get_latest(session):
    latest = session.query(LatestChange).first()
    if latest and latest.serial:
        return latest.serial
    return 0

def set_latest(session, serial):
    latest = session.query(LatestChange).first()
    if latest is None:
        latest = LatestChange()
        session.add(latest)
    if latest.serial and latest.serial < serial:
        latest.serial = serial

def copy_all(src, session):
    batch = 1
    n = 0
    for name in src.packages():
        pkg_add(session, src, name)
        n = n + 1
        if n == batch:
            print(".", end="", flush=True)
            try:
                session.commit()
            except IntegrityError:
                print("\nERROR: ", name)
                raise
            n = 0
    set_latest(session, src.latest())
    print("OK", flush=True)

