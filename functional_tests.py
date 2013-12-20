import unittest
from datetime import datetime
from sqlalchemy import create_engine
import wensleydale
import wensleydale.sources

class TestSources(unittest.TestCase):
    """Check functionality of data sources"""

    def test_standard_sources(self):
        """The null and pypi sources should exist"""
        self.assertNotEqual(wensleydale.sources.null, None)
        self.assertNotEqual(wensleydale.sources.pypi, None)

    def test_null_source(self):
        """THe null source should respond to all standard queries with no data"""
        null = wensleydale.sources.null
        self.assertEqual(null.packages(), [])
        self.assertEqual(null.versions('foo', include_hidden=True), [])
        self.assertEqual(null.changes_since(date=datetime.now()), [])
        self.assertEqual(null.changes_since(serial=100), [])


class TestDatabase(unittest.TestCase):
    """Basic database management tests"""

    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.db = wensleydale.DB(self.engine)
    def tearDown(self):
        self.engine.dispose()

    def test_init(self):
        """The init method should create the schema"""
        self.db.init()
        # TODO: Needs a bit of work, obviously
        # self.assertEqual(self.db.tables, [...])

    def test_load_packages(self):
        """We can load a whole package at once into the database"""
        self.db.load('setuptools')

    def test_load_version(self):
        """We can load just one version into the database"""
        self.db.load('pip', '1.4.1')

    def test_load_existing_version(self):
        """If we try to load a version into the database that's already there, we get an error"""
        self.db.load('pip', '1.4.1')
        self.assertRaises(wensleydale.DatabaseError, self.db.load, 'pip', '1.4.1')

if __name__ == '__main__':
    unittest.main()
