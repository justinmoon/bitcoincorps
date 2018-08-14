import datetime
import queue
import socket
import time
from ipaddress import ip_address

import tinydb

from ibd import AddrMessage, Packet, VerackMessage, VersionMessage

VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

q = queue.Queue()
db = tinydb.TinyDB("db.json")
contacted = set()


class Task:
    id = 0

    def __init__(self, address):
        Task.id += 1
        self.id = self.id
        self.address = address
        self.start = None
        self.stop = None
        self.errors = []  # (error, start, stop) tuples
        self.version_payload = None
        self.addr_payload = None

    @property
    def tries(self):
        return len(self.errors)

    def run(self):
        start = time.time()
        try:
            sock = connect(self.address)

            # FIXME
            version_payload, addr_payload = get_payloads(sock)
            self.version_payload = list(version_payload)
            self.addr_payload = list(addr_payload)

            self.start = start
            self.stop = time.time()
            print("done")
        except Exception as e:
            stop = time.time()
            self.errors.append((str(e), start, stop))
            # FIXME
            q.put(self)
            print(e)
        finally:
            self.save()

    def to_json(self):
        pass

    def from_json(self):
        pass

    def save(self):
        db.insert(self.__dict__)


def get_payloads(sock):
    start = time.time()
    global contacted
    version_payload = None
    addr_payload = None
    while not (version_payload and addr_payload):
        pkt = Packet.from_socket(sock)
        print(pkt.command)
        if pkt.command == b"version":
            version_payload = pkt.payload
            res = Packet(command=b"verack", payload=b"")
            sock.send(res.to_bytes())
        if pkt.command == b"verack":
            getaddr = Packet(command=b"getaddr", payload=b"")
            sock.send(getaddr.to_bytes())
        if pkt.command == b"addr":
            addr_message = AddrMessage.from_bytes(pkt.payload)
            if len(addr_message.address_list) == 1:
                # wait until they send us a useful list of addrs ...
                continue
            else:
                for address in addr_message.address_list:  # FIXME
                    ip = (
                        address.ip.ipv4_mapped.compressed
                        if address.ip.ipv4_mapped
                        else address.ip.compressed
                    )
                    tup = (ip, address.port)  # FIXME
                    if tup not in contacted:
                        q.put(Task(tup))
                addr_payload = pkt.payload
        if time.time() - start > 30:
            raise Exception("taking too long")
    return version_payload, addr_payload


def timestamp():
    return datetime.datetime.now().isoformat()


def connect(address):
    ipv4 = ip_address(address[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    sock = socket.socket(param)
    sock.settimeout(30)
    sock.connect(address)
    sock.send(VERSION)
    return sock


def worker():
    while True:
        task = q.get()
        print(f"connecting to {task.address}. {q.qsize()} tasks queued")
        task.run()


def main(addresses):
    for address in addresses:
        q.put(Task(address))
    worker()


if __name__ == "__main__":
    addresses = [
        ("91.221.70.137", 8333),
        ("92.255.176.109", 8333),
        ("94.199.178.17", 8333),
        ("213.250.21.112", 8333),
    ]
    main(addresses)
