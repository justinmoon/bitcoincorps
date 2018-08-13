import queue
import socket
import threading
import time
from ipaddress import ip_address

from tinydb import Query, TinyDB

from ibd import AddrMessage, Packet, VerackMessage, VersionMessage

db = TinyDB("db.json")
errors_db = TinyDB("errors.json")

# FIXME
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


def log(msg):
    thread_name = threading.currentThread().name
    print(f"({thread_name}) - {msg}")


def _connect(address):
    ipv4 = ip_address(address[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    sock = socket.socket(param)
    sock.settimeout(30)
    sock.connect(address)
    sock.send(VERSION)
    return sock


def get_version_payload(sock):
    result = None
    while True:
        pkt = Packet.from_socket(sock)
        if pkt.command == b"version":
            result = pkt.payload
            res = Packet(command=b"verack", payload=b"")
            sock.send(res.to_bytes())
        if pkt.command == b"verack":
            getaddr = Packet(command=b"getaddr", payload=b"")
            sock.send(getaddr.to_bytes())
            return result


def get_addr_payload(sock):
    while True:
        pkt = Packet.from_socket(sock)
        if pkt.command == b"addr":
            addr_message = AddrMessage.from_bytes(pkt.payload)
            if len(addr_message.address_list) == 1:
                print(f"skipping addr message with only one address")
            else:
                print(pkt.payload)
                return pkt.payload


class Queues:
    address = queue.Queue()
    payload = queue.Queue()
    error = queue.Queue()


def downloader(queues):
    while True:
        # TODO: error handling
        address = queues.address.get()
        try:
            sock = _connect(address)
            version_payload = get_version_payload(sock)
            addr_payload = get_addr_payload(sock)
            payloads = (address, version_payload, addr_payload)
            queues.payload.put(payloads)
        except Exception as e:
            queues.error.put((address, e))
        log(f"downloaded payloads from {address}")


def payloads_pipeline(queues):
    contacted = set()
    while True:
        peer_address, version_payload, addr_payload = queues.payload.get()
        db.insert(
            {"type": "version", "peer": peer_address, "version": list(version_payload)}
        )
        db.insert({"type": "addr", "peer": peer_address, "addr": list(addr_payload)})

        addr_message = AddrMessage.from_bytes(addr_payload)
        for address in addr_message.address_list:
            if address.ip.compressed not in contacted:
                ip = (
                    address.ip.ipv4_mapped.compressed
                    if address.ip.ipv4_mapped
                    else address.ip.compressed
                )
                tup = (ip, address.port)  # FIXME
                queues.address.put(tup)
                contacted.add(address.ip.compressed)  # FIXME hack

        log(f"processed payloads from {peer_address}")


def error_pipeline(queues):
    while True:
        address, error = queues.error.get()
        errors_db.insert({"type": "error", "peer": address, "error": str(error)})
        print(error)
        log(f"wrote error encountered connecting to {address}")


def spawn(downloaders=20, payload_pipelines=1, error_pipelines=1):
    queues = Queues()
    downloader_threads = []
    payload_pipeline_threads = []
    error_pipeline_threads = []
    for i in range(downloaders):
        thread = threading.Thread(
            target=downloader, name=f"downloader-{i}", args=(queues,)
        )
        downloader_threads.append(thread)
        thread.start()
    for i in range(payload_pipelines):
        thread = threading.Thread(
            target=payloads_pipeline, name=f"payload-pipeline-{i}", args=(queues,)
        )
        payload_pipeline_threads.append(thread)
        thread.start()
    for i in range(error_pipelines):
        thread = threading.Thread(
            target=error_pipeline, name=f"error-pipeline-{i}", args=(queues,)
        )
        error_pipeline_threads.append(thread)
        thread.start()
    return queues, downloader_threads, payload_pipeline_threads, error_pipeline_threads


def main():
    db.purge()
    errors_db.purge()
    queues, downloader_threads, payload_pipeline_threads, error_pipeline_threads = (
        spawn()
    )

    addresses = [
        ("91.221.70.137", 8333),
        ("92.255.176.109", 8333),
        ("94.199.178.17", 8333),
        ("213.250.21.112", 8333),
    ]
    for address in addresses:
        queues.address.put(address)

    for t in downloader_threads:
        t.join()  # FIXME hack so program doesn't exit


def test():
    address = ("46.226.18.135", 8333)
    sock = _connect(address)
    version_payload = get_version_payload(sock)
    addr_payload = get_addr_payload(sock)
    payloads = (address, version_payload, addr_payload)


if __name__ == "__main__":
    main()
