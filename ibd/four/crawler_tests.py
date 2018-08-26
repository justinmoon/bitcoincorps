import sqlite3
import time

import pytest

from ibd.four.crawler import *
from ibd.three.complete import Address


@pytest.fixture(scope="function")
def db(tmpdir):
    # FIXME do this in-memory
    import os

    f = os.path.join(tmpdir.strpath, "test.db")

    conn = sqlite3.connect(f)
    create_tables(conn)
    yield conn
    conn.close()


def test_fixture(db):
    addresses = db.execute("select * from addresses").fetchall()
    assert len(addresses) == 0

    _addresses = [
        Address(None, "8.8.8.8", 8333, None, id_=0),
        Address(None, "6.6.6.6", 8333, None, id_=1),
        Address(None, "4.4.4.4", 8333, None, id_=2),
    ]
    insert_addresses(_addresses, db)
    addresses = db.execute("select * from addresses").fetchall()
    assert len(addresses) == 3

    connection = Connection(address=_addresses[0], worker="worker-1")
    connection.start = time.time() - 5
    connection.stop = time.time() - 1
    connection.error = None
    insert_connection(connection, db)
    addresses = db.execute("select * from connections").fetchall()
    assert len(addresses) == 1
