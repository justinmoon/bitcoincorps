import ipaddress

import curio

from ibd import *

# FIXME
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

TIMEOUT = 3


def make_worker(func, in_q, out_q):
    def wrapped():
        while True:
            val = exc = None
            try:
                task = in_q.get(TIMEOUT + .5)
            except queue.Empty:
                break
            try:
                val = func(task)
            except Exception as e:
                exc = e
            out_q.put((val, exc, task))

    return wrapped


def retrieve(q):
    while True:
        try:
            yield q.get(timeout=1)
        except queue.Empty:
            break


def get_version_message(address_tuple):
    # FIXME ugly
    # FIXME onion addresses
    ipv4 = ip_address(address_tuple[0]).version == 4
    param = curio.socket.AF_INET if ipv4 else curio.socket.AF_INET6

    sock = socket.socket(param, socket.SOCK_STREAM)
    sock.settimeout(3)  # wait 3 second for connections / responses
    sock.connect(address_tuple)
    sock.send(OUR_VERSION)
    packet = Packet.from_socket(sock)
    version_message = VersionMessage.from_bytes(packet.payload)
    sock.close()
    return version_message


async def loop(sock):
    while True:
        try:
            pkt = await Packet.async_from_socket(sock)
            print(f"received {pkt.command}")
            if pkt.command == b"version":
                msg = VersionMessage.from_bytes(pkt.payload)
                # TODO send verack
                res = Packet(command=b"verack", payload=b"")
                await sock.send(res.to_bytes())
            elif pkt.command == b"verack":
                msg = VerackMessage.from_bytes(pkt.payload)
                await curio.sleep(.5)
                getaddr = Packet(command=b"getaddr", payload=b"")
                await sock.send(getaddr.to_bytes())
            elif pkt.command == b"addr":
                print(pkt.payload)
        except RuntimeError as e:
            print(e)
            continue
        except Exception as e:
            print("Unhandled exception:", e)
            break


async def connect_async(address):
    ipv4 = ip_address(address[0]).version == 4
    param = curio.socket.AF_INET if ipv4 else curio.socket.AF_INET6
    sock = curio.socket.socket(param)
    # curio.timeout_after(sock.connect, addr)
    await sock.connect(address)
    await sock.send(VERSION)
    await loop(sock)
    await sock.close()


if __name__ == "__main__":
    address = ("85.234.209.217", 8333)
    curio.run(connect_async, address)
