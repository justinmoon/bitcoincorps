import datetime
import queue
import socket
from ipaddress import ip_address

import tinydb

from ibd import AddrMessage, Packet, VerackMessage, VersionMessage

VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

q = queue.Queue()
db = tinydb.TinyDB("db.json")


def get_payloads(sock):
    version_payload = None
    addr_payload = None
    while not (version_payload and addr_payload):
        pkt = Packet.from_socket(sock)
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
                addr_payload = pkt.payload
    return version_payload, addr_payload


# FIXME: make a `Result` class and just save that ...
def save_version_payload(address, payload):
    db.insert(
        {"type": "version", "peer": address, "data": list(payload), "time": timestamp()}
    )


def timestamp():
    return datetime.datetime.now().isoformat()


def save_addr_payload(address, payload):
    db.insert(
        {"type": "addr", "peer": address, "data": list(payload), "time": timestamp()}
    )


def save_error(address, error):
    db.insert(
        {"type": "error", "peer": address, "data": str(error), "time": timestamp()}
    )


def connect(address):
    ipv4 = ip_address(address[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    sock = socket.socket(param)
    sock.settimeout(30)
    sock.connect(address)
    sock.send(VERSION)
    return sock


def crawl():
    successes = 0
    failures = 0
    while True:
        address = q.get()
        try:
            sock = connect(address)
            version_payload, addr_payload = get_payloads(sock)
            save_version_payload(address, version_payload)
            save_addr_payload(address, addr_payload)
            successes += 1
        except Exception as e:
            save_error(address, e)
            failures += 1
        print(f"{successes}/{successes+failures}")


def main(addresses):
    for address in addresses:
        q.put(address)
    crawl()


if __name__ == "__main__":
    addresses = [
        ("91.221.70.137", 8333),
        ("92.255.176.109", 8333),
        ("94.199.178.17", 8333),
        ("213.250.21.112", 8333),
    ]
    main(addresses)
