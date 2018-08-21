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


def test_version_message_to_bytes():
    pkt = Packet(command=version_message.command, payload=version_message.to_bytes())
    print(len(version_message.to_bytes()))
    pkt_bytes = pkt.to_bytes()
    pkt2 = Packet.from_socket(FakeSocket(pkt_bytes))
    version_message_2 = VersionMessage.from_bytes(pkt2.payload)
    print(len(version_message_2.to_bytes()))

    pkt3 = Packet(command=version_message.command, payload=version_message_2.to_bytes())
    print("packets 1 & 2 equal: ", pkt.payload == pkt2.payload)
    print("packets 2 & 3 equal: ", pkt3.payload == pkt2.payload)

    print(version_message)
    print(version_message_2)
    assert version_message.__dict__ == version_message_2.__dict__


def test_services_helpers():
    pass
