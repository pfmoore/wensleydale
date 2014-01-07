import wensleydale
import sqlalchemy.engine

def test_create_db():
    """We can create a new database"""
    db = wensleydale.DB()

def test_db_has_engine():
    """A database object has an engine attribute that is a SQLAlchemy engine"""
    db = wensleydale.DB()
    assert isinstance(db.engine, sqlalchemy.engine.Engine)

def test_db_has_required_tables():
    """After initialisation,  database has the expected tables"""
    db = wensleydale.DB()
    db.create_schema()
    assert 'packages' in set(db.engine.table_names())

def test_model():
    """Do we have package objects"""
    from wensleydale.model import Package
    p = Package()
    p.name = "setuptools"
    db = wensleydale.DB()
    db.create_schema()
    s = db.session()
    s.add(p)
    assert s.query(Package).count() == 1
