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

    insert_addresses(
        [
            Address(None, "8.8.8.8", 8333, None),
            Address(None, "6.6.6.6", 8333, None),
            Address(None, "4.4.4.4", 8333, None),
        ],
        db,
    )

    addresses = db.execute("select * from addresses").fetchall()
    assert len(addresses) == 3
