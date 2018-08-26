import queue
import random
import socket
import sqlite3
import sys
import threading
import time

from tabulate import tabulate

from ibd.three.complete import AddrMessage, Packet

DB_FILE = "mvp.db"

db = sqlite3.connect(DB_FILE)

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
        self.timeout = 60 * 3

    @property
    def tuple(self):
        return (self.ip, self.port)

    def make_socket(self):
        ip_version = socket.AF_INET6 if ":" in self.ip else socket.AF_INET
        sock = self.socket = socket.socket(ip_version)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock

    def handle_version(self, packet):
        self.version_payload = packet.payload
        my_verack_packet = Packet(
            command=b"verack", payload=b""
        )  # FIXME: payload should default to b""
        self.socket.send(my_verack_packet.to_bytes())

    def handle_verack(self, packet):
        my_getaddr_packet = Packet(command=b"getaddr", payload=b"")
        self.socket.send(my_getaddr_packet.to_bytes())

    def handle_addr(self, packet):
        addr_message = AddrMessage.from_bytes(packet.payload)
        # ignore "addr" messages containing just 1 address
        if addr_message.addresses[0].ip != self.ip:
            print("GOT REAL ADDRS")
            self.addr_payload = packet.payload

    def handle_packet(self, packet):
        command_to_handler = {
            b"version": self.handle_version,
            b"verack": self.handle_verack,
            b"addr": self.handle_addr,
        }
        if packet.command in command_to_handler:
            handler = command_to_handler[packet.command]
            handler(packet)

    def check_for_timeout(self):
        now = time.time()
        duration = now - self.worker_start
        needs_timout = duration > self.timeout
        if needs_timout:
            # Let's not treat this as an error for the moment
            # raise Exception("taking too long")
            raise RuntimeError("Taking too long")

    def _connect(self):
        time.sleep(random.random() * 3)
        self.socket.connect(self.tuple)
        self.socket.send(VERSION)
        while not self.addr_payload:
            self.check_for_timeout()
            try:
                packet = Packet.from_socket(self.socket)
            except EOFError as e:
                # For now we ditch this connection
                raise e
            except Exception as e:
                print("Packet.from_socket() error:", e)
                continue
            self.handle_packet(packet)

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
        self.work_queue = work_queue
        self.update_queue = update_queue

    def run(self):
        print(f"starting {self.name}")
        time.sleep(random.random() * 10)  # space things out a bit
        while True:
            address = self.work_queue.get()

            # Tell the crawler we've claimed the task
            address.worker_start = time.time()
            address.worker = self.name
            self.update_queue.put(address)

            address.connect()

            # Tell the crawler about the result of the connection attempt
            self.update_queue.put(address)


class Crawler:
    def __init__(self, num_workers):
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

    def handle_update(self, address):
        update_address(address)

        # FIXME: this is the worst chunk of code i've ever written
        # The problems is that we're working with 2 separate notions of "address"
        if address.addr_payload:
            addr_message = AddrMessage.from_bytes(address.addr_payload)
            print("Received new addresses: ", addr_message.addresses)
            foo = [
                Address(addr_message_address.ip, addr_message_address.port)
                for addr_message_address in addr_message.addresses
            ]
            insert_addresses(foo)

    def crawl(self):
        self.spawn_workers()
        while True:
            # Refill the queue if it is empty
            if self.work_queue.qsize() < 100:
                for address in next_addresses(db):
                    self.work_queue.put(address)

            # Persist the updates to SQLite
            while self.update_queue.qsize():
                address = self.update_queue.get()
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


def create_tables():
    with db:
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
        db.execute(
            "CREATE UNIQUE INDEX idx_address_ip_and_port ON addresses (ip, port)"
        )


def drop_tables():
    with db:
        db.execute("DROP TABLE addresses")


def recreate_tables():
    with db:
        drop_tables(db)
        create_tables(db)


def insert_addresses(addresses):
    # Attempt to insert the address
    # If it already exists in the database, disregard
    for address in addresses:
        with db:
            try:
                db.execute(
                    "INSERT INTO addresses VALUES (:ip, :port, :worker, :worker_start, :worker_stop, :version_payload, :addr_payload, :error)",
                    address,
                )
            except sqlite3.IntegrityError:
                return


def update_address(address):
    with db:
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
        LIMIT 100
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
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def completed_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE version_payload IS NOT NULL
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
    return sorted(result, key=lambda r: -int(r[0].split("-")[1]))
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
        # Address("91.221.70.137", 8333),
        # Address("92.255.176.109", 8333),
        # Address("94.199.178.17", 8333),
        # Address("213.250.21.112", 8333),
        # ]
        # insert_addresses(addresses)
        addresses = []
        Crawler(500).crawl()
    if sys.argv[1] == "monitor":
        report()
