from xmlrpc.client import ServerProxy, ProtocolError
import json
import sys
import os

PYPI_URL = 'http://pypi.python.org/pypi'
pypi = ServerProxy(PYPI_URL)

def initial_load():
    max_serial = latest_serial = pypi.changelog_last_serial()
    min_serial = 1
    min_serial = 764434
    max_serial = 764438
    next_serial = (max_serial + min_serial) // 2

    while next_serial > min_serial:
        print("Trying {}... ".format(next_serial), end="", flush=True)
        try:
            changes = pypi.changelog_since_serial(next_serial)
        except ProtocolError:
            print("Not OK")
            min_serial = next_serial
        else:
            print("OK")
            max_serial = next_serial
        next_serial = (max_serial + min_serial) // 2

    # next_serial is the oldest serial we can get
    # changes is the list of all changes since then
    return [next_serial, changes]

def update(last_serial, changes):
    new_serial = pypi.changelog_last_serial()
    print("Loading from {} to {}... ".format(last_serial, new_serial), end="", flush=True)
    try:
        more_changes = pypi.changelog_since_serial(last_serial)
    except ProtocolError:
        print("Not OK")
        return False
    print("OK")
    changes.extend(more_changes)
    return [new_serial, changes]

if __name__ == '__main__':
    filename = 'changes.json'
    backup = 'changes.json.bak'
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        data = initial_load()
        with open(filename, 'w') as f:
            json.dump(data, f)
    else:
        with open(filename) as f:
            last_serial, changes = json.load(f)
        data = update(last_serial, changes)
        if data:
            os.replace(filename, backup)
            with open(filename, 'w') as f:
                json.dump(data, f)

