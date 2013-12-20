class DatabaseError(Exception): pass

class DB:
    def __init__(self, engine):
        self.engine = engine
        self.packages = set()
        self.old_packages = set()
    def init(self):
        pass
    def commit(self):
        self.old_packages = set(self.packages)
    def rollback(self):
        self.packages = set(self.old_packages)
    def load(self, package, version=None):
        if (package, version) in self.packages:
            raise DatabaseError("Package {}/{} already present".format(package, version))
        self.packages.add((package, version))
