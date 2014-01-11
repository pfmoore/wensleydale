from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy import func
import datetime

Base = declarative_base()

class Package(Base):
    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True, nullable=False)
    releases = relationship("Release", backref="package",
            cascade="all, delete-orphan")

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Package(name={})>".format(self.name)

class Release(Base):
    __tablename__ = 'releases'

    id = Column(Integer, primary_key=True)

    package_id = Column(Integer, ForeignKey('packages.id'), nullable=False)
    version = Column(String, nullable=False)

    stable_version = Column(String)

    author = Column(String)
    author_email = Column(String)
    maintainer = Column(String)
    maintainer_email = Column(String)

    home_page = Column(String)
    license = Column(String)
    summary = Column(String)
    description = Column(String)
    keywords = Column(String)

    platform = Column(String)
    requires_python = Column(String)

    download_url = Column(String)
    bugtrack_url = Column(String)
    docs_url = Column(String)
    package_url = Column(String)
    release_url = Column(String)

    _pypi_hidden = Column(Boolean)
    _pypi_ordering = Column(Integer)
    cheesecake_code_kwalitee_id = Column(String)
    cheesecake_documentation_id = Column(String)
    cheesecake_installability_id = Column(String)

    project_url = Column(String)

    dependencies = relationship("Dependency", backref="release",
            cascade="all, delete-orphan")
    classifiers = relationship("Classifier", backref="release",
            cascade="all, delete-orphan")
    project_urls = relationship("ProjectURL", backref="release",
            cascade="all, delete-orphan")
    urls = relationship("URL", backref="release",
            cascade="all, delete-orphan")
    download_stats = relationship("DownloadStats", backref="release",
            cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('package_id', 'version', name='release_version_uq'),
    )

    def __init__(self, version):
        self.version = version

    def __repr__(self):
        return "<Release(version={})>".format(self.version)

class Dependency(Base):
    __tablename__ = 'dependencies'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    # Check: valid values are
    #   provides, provides_dist, requires, requires_dist, requires_external, obsoletes, obsoletes_dist
    dep_type = Column(String, primary_key=True)

    req = Column(String, nullable=False)

    def __repr__(self):
        return "<Dependency(type={}, req={})>".format(self.dep_type, self.req)

class Classifier(Base):
    __tablename__ = 'classifiers'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    classifier = Column(String, nullable=False)

    def __repr__(self):
        return "<Classifier({})>".format(self.classifier)

class ProjectURL(Base):
    __tablename__ = 'project_urls'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    url = Column(String, nullable=False)

    def __repr__(self):
        return "<ProjectURL(url={})>".format(self.url)

class URL(Base):
    __tablename__ = 'urls'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    url = Column(String, nullable=False)

    filename = Column(String)
    has_sig = Column(Boolean)
    md5_digest = Column(String)

    comment_text = Column(String)
    packagetype = Column(String)
    python_version = Column(String)

    downloads = Column(Integer)
    size = Column(Integer)
    upload_time = Column(DateTime)

    def __repr__(self):
        return "<URL(url={})>".format(self.url)

class DownloadStats(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    filename = Column(String, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    last_month = Column(Integer)
    last_week = Column(Integer)
    last_day = Column(Integer)

    def __repr__(self):
        return "<Downloads(filename={}, timestamp={})>".format(self.filename, self.timestamp)

class Change(Base):
    __tablename__ = 'changes'
    name = Column(String, nullable=False)
    version = Column(String)
    timestamp = Column(DateTime, nullable=False)
    action = Column(String)
    serial = Column(Integer, primary_key=True)
    def __repr__(self):
        return "<Change(serial={}, name={}, version={})>".format(self.serial, self.name, self.version)

def new_package(package, versions=None):
    # package: string
    # version: [string]
    p = Package(package)
    if versions:
        p.releases = [Release(ver) for ver in versions]
    return p

reldata_keys = [
    'stable_version',
    'author',
    'author_email',
    'maintainer',
    'maintainer_email',
    'home_page',
    'license',
    'summary',
    'description',
    'keywords',
    'platform',
    'requires_python',
    'download_url',
    'bugtrack_url',
    'docs_url',
    'package_url',
    'release_url',
    '_pypi_hidden',
    '_pypi_ordering',
    'cheesecake_code_kwalitee_id',
    'cheesecake_documentation_id',
    'cheesecake_installability_id',
]

reldata_deps = [
    'provides',
    'requires',
    'obsoletes',
    'provides_dist',
    'requires_dist',
    'obsoletes_dist',
    'requires_external',
]

def set_release_data(r, data, urls):
    for k in reldata_keys:
        if k in data:
            setattr(r, k, data[k])
    for k in reldata_deps:
        if k in data:
            l = []
            for i, req in enumerate(data[k]):
                d = Dependency()
                d.dep_type = k
                # d.id = i
                d.req = req
                l.append(d)
            setattr(r, k, l)
    l = []
    for i, url in enumerate(data.get('project_urls', [])):
        u = ProjectURL()
        # u.id = i
        u.url = url
        l.append(c)
    r.project_urls = l
    l = []
    for i, classifier in enumerate(data.get('classifiers', [])):
        c = Classifier()
        # c.id = i
        c.classifier = classifier
        l.append(c)
    r.classifiers = l
    r.urls = [new_url(url) for url in urls]

def new_url(urldata):
    u = URL()
    u.url = urldata['url']
    u.filename = urldata.get('filename', '')
    u.has_sig = int(urldata.get('has_sig', 0))
    u.md5_digest = urldata.get('md5_digest')
    u.comment_text = urldata.get('comment_text', '')
    u.packagetype = urldata.get('packagetype', '')
    u.python_version = urldata.get('python_version', '')
    u.downloads = int(urldata.get('downloads', 0))
    u.size = int(urldata.get('size', 0))
    if 'upload_time' in urldata:
        upl = datetime.datetime.strptime(urldata['upload_time'], '%Y-%m-%dT%H:%M:%S')
        u.upload_time = upl
    return u
