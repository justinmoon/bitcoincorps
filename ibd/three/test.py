import time
from io import BytesIO

from .complete import *


class FakeSocket:
    def __init__(self, bytes_):
        self.stream = BytesIO(bytes_)

    def recv(self, n):
        return self.stream.read(n)


services = 1
my_ip = "7.7.7.7"
peer_ip = "6.6.6.6"
port = 8333
now = int(time.time())

# addresses in version messages don't have "time" attributes
my_address = Address(services, my_ip, port, time=None)
peer_address = Address(services, peer_ip, port, time=None)

version_message = VersionMessage(
    version=70015,
    services=services,
    time=now,
    addr_from=my_address,
    addr_recv=peer_address,
    nonce=73948692739875,
    user_agent=b"bitcoin-corps",
    start_height=0,
    relay=1,
)


def test_version_message_round_trip():
    version_message_bytes = version_message.to_bytes()
    packet = Packet(command=version_message.command, payload=version_message_bytes)
    packet_bytes = packet.to_bytes()
    sock = FakeSocket(packet_bytes)
    packet_2 = Packet.from_socket(sock)
    version_message_2 = VersionMessage.from_bytes(packet_2.payload)
    assert version_message == version_message_2


def test_services():
    services = 1 + 2 + 4 + 8 + 1024
    keys = [
        "NODE_NETWORK",
        "NODE_GETUTXO",
        "NODE_BLOOM",
        "NODE_WITNESS",
        "NODE_NETWORK_LIMITED",
    ]
    for key in keys:
        assert lookup_services_key(services, key)
    services = 0
    for key in keys:
        assert not lookup_services_key(services, key)


def test_ip_addresses():
    ipv4_bytes = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x01\x01\x01\x01"
    ipv6_bytes = b"\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07\x07"

    ipv4 = bytes_to_ip(ipv4_bytes)
    assert ipv4 == "1.1.1.1"
    assert ipv4_bytes == ip_to_bytes(ipv4)

    ipv6 = bytes_to_ip(ipv6_bytes)
    assert ipv6 == "707:707:707:707:707:707:707:707"
    assert ipv6_bytes == ip_to_bytes(ipv6)


def test_parse_addrs():
    raw_addr_payload = b"\x013\xf6|[\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff#\xc6\x97\x15 \x8d"
    addr = AddrMessage.from_bytes(raw_addr_payload)
    assert len(addr.addresses) == 1
    address = addr.addresses[0]
    assert address.port == 8333
    assert address.ip == "35.198.151.21"
