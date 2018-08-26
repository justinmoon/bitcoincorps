import sqlite3
import time

import pytest

import handing_threads
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
        Address(None, "8.8.8.8", 8333, None),
        Address(None, "6.6.6.6", 8333, None),
        Address(None, "4.4.4.4", 8333, None),
    ]
    insert_addresses(_addresses, db)
    addresses = db.execute("select * from addresses").fetchall()
    assert len(addresses) == 3

    na = next_addresses(db)
    assert len(na) == 3

    # completed task
    address = _addresses[1]
    address.id = 1

    connection = Connection(address=address, worker="worker-1")
    connection.start = time.time() - 5
    connection.stop = time.time() - 1
    connection.error = None
    connection.version_message = b"version"
    connection.addr_message = b"addr"
    save_connection(connection, db)

    addresses = db.execute("select * from connections").fetchall()
    assert len(addresses) == 1

    addresses = db.execute("select * from version_messages").fetchall()
    assert len(addresses) == 1

    addresses = db.execute("select * from addr_messages").fetchall()
    assert len(addresses) == 1

    assert len(next_addresses(db)) == 2  # one address has been seized

    # # queued task
    # connection = Connection(address=_addresses[1], worker="worker-2")
    # save_connection(connection, db)

    # assert len(next_addresses(db)) == 1

    print(db.execute("select address_id from connections").fetchall())
    print(db.execute("select id from addresses").fetchall())
    print(
        db.execute(
            "select * from addresses where addresses.id not in (select address_id from connections)"
        ).fetchall()
    )
