import sqlite3
import threading

DB_FILE = "crawler.db"


def mvp_save_everything(c):
    pass


def mvp_next_address(c):
    pass


def next_address(c):
    pass


# these all need a sqlite connection ...
def save_version(c):
    pass


def save_addresses(addresses):
    # feeding the queue ...
    pass


def save_addrs(c):
    pass


def save_error(c):
    pass


def save_connection(c):
    pass


class Crawler:
    def __init__(self, addresses, num_workers=100):
        self.workers = []
        self.num_workers = num_workers
        save_addresses(addresses)

    def spawn(self):
        # start the workers
        pass

    def loop(self):
        # restart dead threads?
        pass


class Worker(threading.Thread):
    def __init__(self, crawler, number):
        super(Worker, self).__init__()
        self.name = f"worker-{number}"
        self.db = sqlite3.connect(DB_FILE)  # FIXME how to pass this to the connection?

    def run(self):
        while True:
            address = next_address()
            c = Connection(address)
            c.save()  # so that our reporting script know's what this worker is doing ...
            try:
                c.connect()
            except Exception as e:
                self.error = e
            finally:
                c.save()


# Maybe call this task? Only the db has separate idea of "connection"
# this whole class could be accomplished just as a function
class Connection:
    def __init__(self, address):
        self.address = address
        self.sock = ...
        self.start = None
        self.stop = None
        self.error = None
        self.version = None
        self.address = None

    def connect(self):
        # does all the bitcoin-specific stuff ...
        # return version, addrs
        pass

    def save(self):
        save_connection(self)
        if self.version:
            save_version(self)
        if self.addrs:
            save_addrs(self)
            save_addresses(...)
        if self.error:
            save_error(self)
