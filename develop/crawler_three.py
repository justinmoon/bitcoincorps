import queue
import socket
import sys
import threading
import time
from ipaddress import ip_address

from tabulate import tabulate
from tinydb import Query, TinyDB

from ibd import AddrMessage, Packet

# Monitoring / Reporting

db = TinyDB("db.json")


def address_pool_size():
    return 5000


def num_tasks():
    return 150


def num_tasks_completed():
    return 50


def num_tasks_failed():
    return 100


def completion_percentage():
    completed = num_tasks_completed()
    total = num_tasks()
    return completed / total


def start_time():
    return time.time() - 10


def completed_per_second():
    start = start_time()
    now = time.time()
    elapsed = now - start
    completed = num_tasks_completed()
    return completed / elapsed


def percentage(value):
    return f"{value:.2%}"


def crawler_report():
    headers = [
        "Address Pool",
        "Got Version",
        "Got Addrs",
        "Exception",
        "Completion %",
        "Tasks / Second",
    ]
    report = db.search(query["type"] == "crawler-report")[0]
    rows = [
        [
            report["address-pool-size"],
            report["got-version"],
            report["got-addrs"],
            report["got-exception"],
            percentage(report["completion-percentage"]),
            report["per-second"],
        ]
    ]
    return tabulate(rows, headers)


query = Query()


def snapshot_to_row(s):
    start = s["start"]
    elapsed = time.time() - start
    return [s["worker"], s["address"], elapsed]


# TODO https://twitter.com/brianokken/status/1029880505750171648
def worker_report():
    headers = ["Worker Name", "Peer Address", "Elapsed"]
    all_snapshots = db.search(query["type"] == "task-report")
    rows = [snapshot_to_row(s) for s in all_snapshots]
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

    w = worker_report()
    length = len(w.split("\n")[0])
    padding_len = round((length - 7) / 2)
    padding = " " * padding_len
    print(padding + "===========" + padding)
    print(padding + "| Workers |" + padding)
    print(padding + "===========" + padding)
    print()
    print(w)


# Persistence


# Crawler

VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


# TODO implement support for "multiple runs" later
# class Run:

# start
# stop
# error
# version_payload
# addr_payllad

# @property
# def duration(self):
# pass


class Crawler:
    def __init__(self, addresses, num_workers=100):
        self.addresses = set(addresses)
        self.work_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.num_workers = num_workers
        # FIXME
        self._num_got_version = 0
        self._num_got_addrs = 0
        self._num_got_exception = 0
        self._start = time.time()

    def report(self):
        if not self._num_got_version:
            return
        return {
            "type": "crawler-report",
            "address-pool-size": len(self.addresses),
            "queue-size": self.work_queue.qsize(),
            "got-version": self._num_got_version,
            "got-addrs": self._num_got_addrs,
            "got-exception": self._num_got_exception,
            "completion-percentage": self._num_got_version
            / (self._num_got_version + self._num_got_exception),
            "per-second": self._num_got_version / (time.time() - self._start),
        }

    @property
    def tasks_remaining(self):
        return self.work_queue.qsize()

    def crawl(self):
        # iterate over wrkers and seee if they're dead, restart if necessary ...
        # or maybe we just need a worker class?
        self.spawn_workers()
        self.feed_workers()
        self.loop()

    def loop(self):
        last_report = time.time()
        while True:
            output = self.result_queue.get()
            if isinstance(output, Task):
                if output.completed:
                    self.handle_completed(output)
                else:
                    self.handle_failed(output)
            else:
                # assume its a report
                db.upsert(output, query["worker"] == output["worker"])

            if time.time() - last_report > 2:
                last_report = time.time()
                report = self.report()
                if report:
                    print("******upserting*********")
                    db.upsert(self.report(), query["type"] == "crawler-report")

    def feed_workers(self):
        # FIXME this is kinda weird ... this method does the right thing
        # only when the program starts up
        for address in self.addresses:
            task = Task(address)
            self.work_queue.put(task)

    def spawn_workers(self):
        for i in range(self.num_workers):
            worker = Worker(self, i)
            self.workers.append(worker)
            worker.start()

    def handle_completed(self, task):
        # print(
        # f"Successfully downloaded version and addr messages from {task.address[0]}"
        # )
        # Fill work_queue with new addresses we hear about
        # FIXME hacks!
        if task.version_payload:
            self._num_got_version += 1
        if task.addr_payload:
            self._num_got_addrs += 1
            addr_message = AddrMessage.from_bytes(task.addr_payload)
            for address in addr_message.address_list:  # FIXME
                if address.tuple not in addresses:
                    self.addresses.add(address.tuple)
                    task = Task(address.tuple)
                    self.work_queue.put(task)

    def handle_failed(self, task):
        # TOOO: check how many times its failed and maybe discard
        print(f"Connection with {task.address[0]} failed: {task.exception}")
        self._num_got_exception += 1
        self.work_queue.put(task)


class Worker(threading.Thread):
    def __init__(self, crawler, number):
        super(Worker, self).__init__()

        self.name = f"worker-{number}"
        self.crawler = crawler

    def run(self):
        print(f"{self.name} starting")
        while True:
            task = self.crawler.work_queue.get()
            # report that we've started the task
            self.crawler.result_queue.put(task.snapshot(self))
            print(f"({self.name}) connecting to {task.address}")
            task.run()
            self.crawler.result_queue.put(task)


class Task:
    id = 0

    def __init__(self, address):
        Task.id += 1
        self.id = self.id
        self.sock = None
        self.address = address
        self.exception = None
        self.version_payload = None
        self.addr_payload = None
        self.start = None

    def snapshot(self, worker):
        # FIXME hack
        if not self.start:
            self.start = time.time()
        return {
            "type": "task-report",
            "worker": worker.name,  # FIXME
            "id": self.id,
            "start": self.start,
            "address": self.address,
        }

    def _run(self):
        timeout = 60  # FIXME
        self.start = start = time.time()
        ipv4 = ip_address(self.address[0]).version == 4
        param = socket.AF_INET if ipv4 else socket.AF_INET6
        sock = self.sock = socket.socket(param)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.connect(self.address)
        sock.send(VERSION)
        while not self.addr_payload:
            pkt = Packet.from_socket(sock)
            print(pkt.command)
            if pkt.command == b"version":
                self.version_payload = pkt.payload
                res = Packet(command=b"verack", payload=b"")
                sock.send(res.to_bytes())
            if pkt.command == b"verack":
                getaddr = Packet(command=b"getaddr", payload=b"")
                sock.send(getaddr.to_bytes())
            if pkt.command == b"addr":
                addr_message = AddrMessage.from_bytes(pkt.payload)
                # ignore "addr" messages containing just 1 address
                if len(addr_message.address_list) > 1:
                    self.addr_payload = pkt.payload
            if time.time() - start > timeout:
                # Let's not treat this as an error for the moment
                # raise Exception("taking too long")
                break

    def run(self):
        try:
            self._run()
        except Exception as exception:
            self.exception = exception
        finally:
            if self.sock:
                self.sock.close()
                del self.sock

    @property
    def completed(self):
        # FIXME "complete" sounds better at the moment...
        # We mainly care about getting the version information from peers ...
        # If we get addrs, that's just extra.
        # But we quickly overwhelm the queue with addrs so let's not hold up the show ...
        return self.version_payload is not None

    @property
    def pending(self):
        return not self.completed and not self.failed

    @property
    def failed(self):
        return self.exception is not None

    def __repr__(self):
        return f"<Task address={self.address}>"


if __name__ == "__main__":
    arg = sys.argv[1]
    if arg == "crawl":
        addresses = [
            ("91.221.70.137", 8333),
            ("92.255.176.109", 8333),
            ("94.199.178.17", 8333),
            ("213.250.21.112", 8333),
        ]
        Crawler(addresses).crawl()
    if arg == "report":
        report()
