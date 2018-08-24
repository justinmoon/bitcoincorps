import queue
import socket
import sqlite3
import time

from ibd.three.complete import AddrMessage, Packet

DB_FILE = "mvp.db"

db = sqlite3.connect(DB_FILE)
q = queue.Queue()

#######################
### For the crawler ###
#######################

VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


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
        self.socket = self.make_socket()
        self.error = error
        self.version_payload = version_payload
        self.addr_payload = addr_payload
        self.timeout = 60  # FIXME

    @property
    def tuple(self):
        return (self.ip, self.port)

    def make_socket(self):
        ip_version = socket.AF_INET6 if ":" in self.ip else socket.AF_INET
        sock = self.socket = socket.socket(ip_version)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.settimeout(???)
        return sock

    def _connect(self):
        self.worker_start = start = time.time()
        self.socket.connect(self.tuple)
        self.socket.send(VERSION)
        while not self.addr_payload:
            pkt = Packet.from_socket(self.socket)
            print(pkt.command)
            if pkt.command == b"version":
                self.version_payload = pkt.payload
                my_verack_pkt = Packet(command=b"verack", payload=b"")
                self.socket.send(my_verack_pkt.to_bytes())
            if pkt.command == b"verack":
                getaddr = Packet(command=b"getaddr", payload=b"")
                self.socket.send(getaddr.to_bytes())
            if pkt.command == b"addr":
                addr_message = AddrMessage.from_bytes(pkt.payload)
                # ignore "addr" messages containing just 1 address
                if len(addr_message.addresses) > 1:
                    self.addr_payload = pkt.payload
            if time.time() - start > self.timeout:
                # Let's not treat this as an error for the moment
                # raise Exception("taking too long")
                break

    def connect(self):
        try:
            self._connect()
        except Exception as exception:
            self.exception = exception
        finally:
            if self.socket:
                self.socket.close()


def main():
    while True:
        address = next_address(db)
        save_address(db, address)

        print(f"Connecting to {address.tuple}")
        address._connect()

        save_address(db, address)


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


def save_address(db, address):
    db.execute(
        "INSERT INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
        address.__dict__,
    )
    db.commit()  # FIXME necessary?


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


if __name__ == "__main__":
    # create_tables(db)
    addresses = [
        ("91.221.70.137", 8333),
        ("92.255.176.109", 8333),
        ("94.199.178.17", 8333),
        ("213.250.21.112", 8333),
    ]
    for address in addresses:
        save_address(db, Address(*address))
    main()
