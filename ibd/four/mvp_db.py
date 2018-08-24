import queue
import socket
import sqlite3
import threading
import time

from ibd.three.complete import AddrMessage, Packet

DB_FILE = "mvp.db"

db = sqlite3.connect(DB_FILE, check_same_thread=False)
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
        self.socket.connect(self.tuple)
        self.socket.send(VERSION)
        while not self.addr_payload:
            try:
                pkt = Packet.from_socket(self.socket)
            except Exception as e:
                continue
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
                    print("GOT REAL ADDRS")
                    self.addr_payload = pkt.payload
            if time.time() - self.worker_start > self.timeout:
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


class Worker(threading.Thread):
    def __init__(self, name):
        super(Worker, self).__init__()
        self.name = name
        self.db = sqlite3.connect(DB_FILE, check_same_thread=False)

    def run(self):
        print(f"starting {self.name}")
        while True:
            with self.db as c:
                # FIXME this is magic
                # this locks down the database to all other connectinos
                # until this connection finishes
                # prevents two threads from grabbing the same task
                # hack in place of an "atomic queue"
                # would a queue be better???
                c.execute("begin exclusive")

                address = next_address(c)
                address.worker_start = time.time()
                address.worker = self.name
                update_address(c, address)

            print(f"{self.name} connecting to {address.tuple}")
            address.connect()

            with self.db as c:
                update_address(c, address)

            # FIXME: this is the worst chunk of code i've ever written
            if address.addr_payload:
                addr = AddrMessage.from_bytes(address.addr_payload)
                print("Received new addresses: ", addr.addresses)
                for _address in addr.addresses:
                    with self.db as c:
                        a = Address(_address.ip, _address.port)
                        insert_address(c, a)


class Crawler:
    def __init__(self, addresses, num_workers):
        self.feed_workers(addresses)
        self.num_workers = num_workers
        self.workers = []

    def spawn_workers(self):
        for i in range(self.num_workers):
            worker_name = f"worker-{i}"
            worker = Worker(worker_name)
            self.workers.append(worker)
            worker.start()

    def feed_workers(self, addresses):
        for address in addresses:
            with db as conn:
                insert_address(conn, Address(*address))

    def crawl(self):
        self.spawn_workers()
        while True:
            time.sleep(1)


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
    db.execute("CREATE UNIQUE INDEX idx_address_ip_and_port ON addresses (ip, port)")


def drop_tables(db):
    db.execute("DROP TABLE addresses")


def recreate_tables(db):
    drop_tables(db)
    create_tables(db)


def insert_address(db, address):
    db.execute(
        "INSERT INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
        address.__dict__,
    )


def update_address(db, address):
    db.execute(
        "REPLACE INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
        address.__dict__,
    )


def next_address(db):
    # FIXME: this blows up when we run out of addresses
    args = db.execute(
        """
        SELECT * FROM addresses
        WHERE worker_start IS NULL
    """
    ).fetchone()
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
    recreate_tables(db)
    addresses = [
        ("91.221.70.137", 8333),
        ("92.255.176.109", 8333),
        ("94.199.178.17", 8333),
        ("213.250.21.112", 8333),
    ]
    Crawler(addresses, 4).crawl()
