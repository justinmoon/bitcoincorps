import queue
import socket
import sqlite3
import sys
import threading
import time

from tabulate import tabulate

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
        self.timeout = 10  # FIXME

    @property
    def tuple(self):
        return (self.ip, self.port)

    def make_socket(self):
        ip_version = socket.AF_INET6 if ":" in self.ip else socket.AF_INET
        sock = self.socket = socket.socket(ip_version)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(5)
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
                if addr_message.addresses[0].ip != self.ip:
                    print("GOT REAL ADDRS")
                    self.addr_payload = pkt.payload
            if time.time() - self.worker_start > self.timeout:
                # Let's not treat this as an error for the moment
                # raise Exception("taking too long")
                self.error = "taking too long"
                return

    def connect(self):
        try:
            self._connect()
        except Exception as e:
            print("ERROR!!!", e)
            self.error = str(e)
        finally:
            if self.socket:
                self.socket.close()


class Worker(threading.Thread):
    def __init__(self, name, work_queue, update_queue):
        super(Worker, self).__init__()
        self.name = name
        self.db = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.work_queue = work_queue
        self.update_queue = update_queue

    def run(self):
        print(f"starting {self.name}")
        while True:
            address = self.work_queue.get()

            # Tell the crawler we've claimed the task
            address.worker_start = time.time()
            address.worker = self.name
            self.update_queue.put(address)

            print(f"{self.name} connecting to {address.tuple}")
            address.connect()

            # Tell the crawler about the result of the connection attempt
            self.update_queue.put(address)


class Crawler:
    def __init__(self, addresses, num_workers):
        self.feed_workers(addresses)
        self.num_workers = num_workers
        self.workers = []
        self.work_queue = queue.Queue()
        self.update_queue = queue.Queue()

    def spawn_workers(self):
        for i in range(self.num_workers):
            worker_name = f"worker-{i}"
            worker = Worker(worker_name, self.work_queue, self.update_queue)
            self.workers.append(worker)
            worker.start()

    def feed_workers(self, addresses):
        for address in addresses:
            with db as conn:
                insert_address(conn, Address(*address))

    def handle_update(self, address):
        with db as c:
            update_address(c, address)

        # FIXME: this is the worst chunk of code i've ever written
        # The problems is that we're working with 2 separate notions of "address"
        if address.addr_payload:
            addr_message = AddrMessage.from_bytes(address.addr_payload)
            print("Received new addresses: ", addr_message.addresses)
            for addr_message_address in addr_message.addresses:
                with db as c:
                    a = Address(addr_message_address.ip, addr_message_address.port)
                    insert_address(c, a)

    def crawl(self):
        self.spawn_workers()
        while True:
            # Refill the queue if it is empty
            if self.work_queue.qsize() < 10:
                for address in next_addresses(db):
                    print("adding work")
                    self.work_queue.put(address)

            # Persist the updates to SQLite
            while self.update_queue.qsize():
                address = self.update_queue.get()
                print("handling update")
                self.handle_update(address)

            count = 0
            for thread in self.workers:
                if thread.is_alive():
                    count += 1
            print(f"Living threads: {count}")
            print(f"Work queue: {self.work_queue.qsize()}")
            print(f"Update queue: {self.update_queue.qsize()}")
            # Don't hammer the CPU
            time.sleep(2)


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
    # Attempt to insert the address
    # If it already exists in the database, disregard
    try:
        db.execute(
            "INSERT INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
            address.__dict__,
        )
    except sqlite3.IntegrityError:
        return


def update_address(db, address):
    db.execute(
        "REPLACE INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
        address.__dict__,
    )


def next_addresses(db):
    # FIXME: this blows up when we run out of addresses
    args_list = db.execute(
        """
        SELECT * FROM addresses
        WHERE worker_start IS NULL
        LIMIT 10
    """
    ).fetchall()
    return [Address(*args) for args in args_list]


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


def worker_statuses(db):
    # TODO: also query count(*) and display that ...
    q = """
    SELECT 
        worker, ip, strftime('%s','now') - MAX(worker_start)
    FROM 
        addresses
    WHERE 
        worker IS NOT NULL 
        AND worker_stop IS NULL
    GROUP BY 
        worker
    """
    result = db.execute(q).fetchall()
    return sorted(result, key=lambda r: int(r[0].split("-")[1]))
    # result = db.execute(q).fetchall()
    # addresses = [Address(*args) for args in result]
    # return sorted(addresses, key=lambda address: int(address.worker.split("-")[1]))


def crawler_report():
    headers = ["Queued", "Completed", "Failed"]
    rows = [[queued_count(db), completed_count(db), failed_count(db)]]
    return tabulate(rows, headers)


# TODO https://twitter.com/brianokken/status/1029880505750171648
def worker_report():
    headers = ["Worker Name", "Peer Address", "Elapsed"]
    rows = worker_statuses(db)
    return tabulate(rows, headers)


def report():
    c = crawler_report()
    length = len(c.split("\n")[0])
    padding_len = round((length - 7) / 2)
    padding = " " * padding_len
    print(padding + "===========" + padding)
    print(padding + "| Crawler |" + padding)
    print(padding + "===========" + padding)
    print()
    print(c)

    print("\n\n")

    print(worker_report())


if __name__ == "__main__":
    if sys.argv[1] == "crawl":
        # recreate_tables(db)
        # addresses = [
        # ("91.221.70.137", 8333),
        # ("92.255.176.109", 8333),
        # ("94.199.178.17", 8333),
        # ("213.250.21.112", 8333),
        # ]
        addresses = []
        Crawler(addresses, 4).crawl()
    if sys.argv[1] == "monitor":
        report()
