import wensleydale2
from sqlalchemy import create_engine
from itertools import groupby
from operator import itemgetter

def list(db, id):
    print("="*10, id, "="*10)
    sql = "select p.name, r.version from packages p, releases r where p.id = r.package_id"
    for n, vers in groupby(db.execute(sql), itemgetter(0)):
        print(n, ', '.join(v.version for v in vers))

# db = create_engine('sqlite:///x.db')
db = create_engine('sqlite://')
src = wensleydale2.JSONSource()

wensleydale2.init(db)

wensleydale2.get(src, db, 'setuptools')
list(db, "Added setuptools")
wensleydale2.get(src, db, 'pip')
list(db, "Added pip")
wensleydale2.remove(db, 'pip', '1.4.1')
list(db, "Removed pip 1.4.1")
wensleydale2.get(src, db, 'pip', '1.4')
list(db, "Refreshed pip 1.4")
wensleydale2.rename(db, 'setuptools', 'distribute')
list(db, "Renamed setuptools")
wensleydale2.remove(db, 'distribute')
list(db, "Removed distribute")
