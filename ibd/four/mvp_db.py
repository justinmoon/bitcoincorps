import socket
import sqlite3

DB_FILE = "mvp.db"

db = sqlite3.connect(DB_FILE)

#######################
### For the crawler ###
#######################


class Address:
    def __init__(
        self,
        ip,
        port,
        worker=None,
        worker_start=None,
        worker_stop=None,
        error=None,
        version_payload=None,
        addr_payload=None,
    ):
        self.ip = ip
        self.port = port
        self.worker = worker
        self.worker_start = worker_start
        self.worker_stop = worker_stop
        # self.socket = socket.socket()
        self.socket = None
        self.error = error
        self.version_payload = version_payload
        self.addr_payload = addr_payload


def create_tables(db):
    db.execute(
        """
        CREATE TABLE addresses (
            ip TEXT,
            port INTEGER,
            worker TEXT,
            worker_start REAL,
            worker_stop REAL,
            version_payload BLOB,
            addr_payload BLOB,
            error TEXT
        )
    """
    )


def save_address(db, connection):
    db.execute(
        "INSERT INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
        connection.__dict__,
    )


def next_address(db):
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT * FROM addresses
        WHERE worker_start IS NULL
    """
    )
    args = cursor.fetchone()
    return Address(*args)


#######################
### For the monitor ###
#######################


def queued_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE worker_start IS NULL
            and worker_stop IS NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def completed_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE version_payload IS NOT NULL
            and addr_payload IS NOT NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def failed_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE error IS NOT NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def total_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def started_count(db):
    # start time + worker non empty, worker_stop empty
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE worker_start IS NOT NULL
            AND worker_stop IS NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def crawler_start_time(db):
    result = db.execute(
        """
        SELECT MIN(worker_start)
        FROM addresses
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result
