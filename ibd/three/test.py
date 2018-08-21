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
