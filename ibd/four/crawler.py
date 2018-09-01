import queue
import random
import socket
import sqlite3
import sys
import threading
import time

from tabulate import tabulate

from ibd.four.monitor import report
from ibd.three.complete import Address, AddrMessage, Packet

DB_FILE = "crawler.db"
db = sqlite3.connect(DB_FILE)

VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


class Connection:
    def __init__(self, address, worker):
        self.address = address
        self.worker = worker
        self.socket = self.make_socket()
        self.start = None
        self.stop = None
        self.error = None
        self.timeout = 180
        # Relationships
        self.version_message = None
        self.addr_message = None

    def start_handshake(self):
        time.sleep(random.random() * 3)
        self.socket.connect(self.address.tuple())
        self.socket.send(VERSION)  # FIXME

    def make_socket(self):
        ip_version = socket.AF_INET6 if ":" in self.address.ip else socket.AF_INET
        sock = self.socket = socket.socket(ip_version)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(15)
        return sock

    def handle_version(self, packet):
        self.version_message = packet.payload
        # FIXME: payload should default to b""
        my_verack_packet = Packet(command=b"verack", payload=b"")
        self.socket.send(my_verack_packet.to_bytes())

    def handle_verack(self, packet):
        my_getaddr_packet = Packet(command=b"getaddr", payload=b"")
        self.socket.send(my_getaddr_packet.to_bytes())

    def handle_addr(self, packet):
        addr_message = AddrMessage.from_bytes(packet.payload)
        if set([address.ip for address in addr_message.addresses]) != set(
            [self.address.ip]
        ):
            self.addr_message = packet.payload

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
        duration = now - self.start
        needs_timout = duration > self.timeout
        if needs_timout:
            # Let's not treat this as an error for the moment
            # raise Exception("taking too long")
            raise RuntimeError("Taking too long")

    def complete(self):
        return self.version_message is not None and self.addr_message is not None

    def _connect(self):
        self.start = time.time()
        self.start_handshake()
        while not self.complete():
            self.check_for_timeout()
            try:
                packet = Packet.from_socket(self.socket)
            except EOFError as e:
                # For now we ditch this connection
                raise e
            except Exception as e:
                continue
            self.handle_packet(packet)

    def connect(self):
        try:
            self._connect()
        except Exception as e:
            self.error = str(e)
        finally:
            if self.socket:
                self.socket.close()


class Worker(threading.Thread):
    def __init__(self, name, address_queue, connection_queue):
        super(Worker, self).__init__()
        self.name = name
        self.address_queue = address_queue
        self.connection_queue = connection_queue

    def run(self):
        print(f"starting {self.name}")
        time.sleep(random.random() * 10)  # space things out a bit
        while True:
            address = self.address_queue.get()
            connection = Connection(
                address, self.name
            )  # FIXME just self for more flexability ...

            connection.connect()

            # Tell the crawler about the result of the connection attempt
            self.connection_queue.put(connection)


class Crawler:
    def __init__(self, num_workers):
        self.num_workers = num_workers
        self.workers = []
        self.address_queue = queue.Queue()
        self.connection_queue = queue.Queue()

    def spawn_workers(self):
        for i in range(self.num_workers):
            worker_name = f"worker-{i}"
            worker = Worker(worker_name, self.address_queue, self.connection_queue)
            self.workers.append(worker)
            worker.start()

    def save_connection_outcome(self, connection):
        save_connection(connection)
        # Save connection.addr_message.addresses as well ...
        if connection.addr_message:
            x = AddrMessage.from_bytes(connection.addr_message)
            insert_addresses(x.addresses)

    def crawl(self):
        self.spawn_workers()
        while True:
            # give the workers tasks
            # Refill the queue if it is empty
            if self.address_queue.qsize() < 100:
                for address in next_addresses():
                    self.address_queue.put(address)

            # processes task results
            # Persist the updates to SQLite
            while self.connection_queue.qsize():
                connection = self.connection_queue.get()
                self.save_connection_outcome(connection)

            print(f"Address queue: {self.address_queue.qsize()}")
            print(f"Connection queue: {self.connection_queue.qsize()}")
            time.sleep(2)


def drop_tables():
    with db:
        db.execute("DROP TABLE IF EXISTS addresses")
        db.execute("DROP TABLE IF EXISTS connections")
        db.execute("DROP TABLE IF EXISTS version_messages")
        db.execute("DROP TABLE IF EXISTS addr_messages")


def recreate_tables():
    with db:
        drop_tables()
        create_tables()


def create_tables(db=db):
    with db:
        db.execute(
            """
            CREATE TABLE addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                port INTEGER
            )
        """
        )
        db.execute(
            "CREATE UNIQUE INDEX idx_address_ip_and_port ON addresses (ip, port)"
        )
        db.execute(
            """
            CREATE TABLE connections (
                id INTEGER PRIMARY KEY,
                worker TEXT,
                start REAL,
                stop REAL,
                error TEXT,
                address_id INTEGER NOT NULL,
                    FOREIGN KEY (address_id) REFERENCES addresses(id)
            )
        """
        )
        db.execute(
            # FIXME columns
            """
            CREATE TABLE addr_messages (
                raw BLOB,
                connection_id INTEGER NOT NULL,
                    FOREIGN KEY (connection_id) REFERENCES connections(id)
            )
        """
        )
        db.execute(
            # FIXME columns
            """
            CREATE TABLE version_messages (
                raw BLOB,
                connection_id INTEGER NOT NULL,
                    FOREIGN KEY (connection_id) REFERENCES connections(id)
            )
        """
        )


def save_connection(connection, db=db):
    with db:
        query = """
            INSERT INTO connections (worker, start, stop, error, address_id)
            VALUES (:worker, :start, :stop, :error, :address_id)
        """
        args = connection.__dict__
        args["address_id"] = connection.address.id
        cursor = db.execute(query, args)

        connection_id = cursor.lastrowid  # kind of a hacky way of getting an cursor ...

        if connection.version_message:
            query = """
                INSERT INTO version_messages (raw, connection_id)
                VALUES (?, ?)
            """
            args = (connection.version_message, connection_id)
            db.execute(query, args)

        if connection.addr_message:
            query = """
                INSERT INTO addr_messages (raw, connection_id)
                VALUES (?, ?)
            """
            args = (connection.addr_message, connection_id)
            db.execute(query, args)


def insert_addresses(addresses, db=db):
    # Attempt to insert the address
    # If it already exists in the database, disregard
    for address in addresses:
        with db:
            try:
                db.execute(
                    "INSERT INTO addresses(ip, port) VALUES (:ip, :port)",
                    address.__dict__,
                )
            except sqlite3.IntegrityError:
                continue


def next_addresses(db=db):
    # FIXME: this blows up when we run out of addresses
    args_list = db.execute(
        """
        SELECT *
        FROM addresses
        WHERE id not in (
            SELECT address_id FROM connections
        )
        LIMIT 100
    """
    ).fetchall()
    # FIXME soooo dirty
    return [Address(None, args[1], args[2], None, id_=args[0]) for args in args_list]


if __name__ == "__main__":
    if sys.argv[1] == "crawl":
        recreate_tables()
        addresses = [
            Address(None, "91.221.70.137", 8333, None),
            Address(None, "92.255.176.109", 8333, None),
            Address(None, "94.199.178.17", 8333, None),
            Address(None, "213.250.21.112", 8333, None),
        ]
        insert_addresses(addresses)
        Crawler(500).crawl()
    if sys.argv[1] == "monitor":
        report()
