class Source:
    def packages(self):
        return []
    def versions(self, package, include_hidden=False):
        return []
    def changes_since(self, date=None, serial=None):
        return []

pypi = Source()
null = Source()
