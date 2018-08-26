import sqlite3
import time

import pytest

from ibd.four.mvp_db import *


@pytest.fixture(scope="function")
def db(tmpdir):
    # FIXME do this in-memory
    import os

    f = os.path.join(tmpdir.strpath, "test.db")

    conn = sqlite3.connect(f)
    create_tables(conn)
    yield conn
    conn.close()


def make_address(state):
    assert state in ("queued", "started", "failed", "completed")
    address = Address(ip="8.8.8.8", port=8333)
    if state != "queued":
        address.worker = "worker-77"
        address.worker_start = time.time() - 10
    if state == "failed":
        address.worker_stop = time.time() - 5
        address.error = "RuntimeError"
    if state == "completed":
        # For now, let's just say that tasks either get both payloads or neither ... TODO
        address.worker_stop = time.time() - 5
        address.version_payload = b"veryold"
        address.addr_payload = b"igotnofriends"
    return address


def test_next_address(db):
    address = make_address(state="queued")
    save_address(db, address)
    na = next_address(db)
    assert address.__dict__ == na.__dict__


def test_fixture(db):
    addresses = db.execute("select * from addresses").fetchall()
    assert len(addresses) == 0


def test_reports(db):
    queued = 5
    started = 4
    completed = 3
    failed = 2
    total = queued + started + completed + failed

    for i in range(queued):
        save_address(db, make_address("queued"))
    for i in range(started):
        save_address(db, make_address("started"))
    for i in range(completed):
        save_address(db, make_address("completed"))
    for i in range(failed):
        save_address(db, make_address("failed"))

    assert queued == queued_count(db)
    assert started == started_count(db)
    assert completed == completed_count(db)
    assert failed == failed_count(db)
    assert total == total_count(db)

    # FIXME: this doesn't actually check that we're getting the min ...
    assert time.time() - 10.1 < crawler_start_time(db) < time.time() - 9.9
