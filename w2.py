#!C:\Work\Projects\wensleydale\ve\Scripts\python.exe

import argparse
import wensleydale2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

def batch_process(lst, batch=100, callback=lambda: None):
    i = 0
    for elem in tqdm(lst):
        yield elem
        i = i + 1
        if i == batch:
            callback()
            i = 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("command", default="update")
    parser.add_argument("--source", default="pypi:")
    parser.add_argument("--db", default="sqlite:///pypi_w.db")
    args = parser.parse_args()

    db = create_engine(args.db)
    Session = sessionmaker(db)
    session = Session()

    if args.source == 'pypi:':
        src = wensleydale2.PYPISource()
    elif args.source is None:
        src = wensleydale2.JSONSource()
    else:
        src = wensleydale2.JSONSource(args.source)

    if args.command == 'create':
        wensleydale2.init(db)
        for name in batch_process(src.packages(), callback=session.commit):
            wensleydale2.pkg_add(session, src, name)
        session.commit()
    elif args.command == 'update':
        serial = wensleydale2.get_latest(session)
        changes = src.changes(serial)
        if changes:
            print("Getting changes from {} to {}".format(serial, max(c[4] for c in changes)))
            for change in batch_process(changes, callback=session.commit, batch=1):
                wensleydale2.process_change(src, session, change)
            session.commit()
