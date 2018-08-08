from ibd.four.complete import Packet
from ibd.two.complete import *

OUR_VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

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
    param = socket.AF_INET if ipv4 else socket.AF_INET6

    sock = socket.socket(param, socket.SOCK_STREAM)
    sock.settimeout(3)  # wait 3 second for connections / responses
    sock.connect(address_tuple)
    sock.send(OUR_VERSION)
    packet = Packet.from_socket(sock)
    version_message = VersionMessage.from_bytes(packet.payload)
    sock.close()
    return version_message


