import socket
import time
from tabulate import tabulate

from ibd.six.utils import (
    read_command, read_magic, read_length, read_checksum, read_payload,
    NETWORK_MAGIC, compute_checksum, int_to_bytes, encode_command,
    fmt,
)
from ibd.six.msg import Address, VersionMessage, VerackMessage


# FIXME: this is a hack
def recover(sock):
    MAGIC_BYTES = b"\xf9\xbe\xb4\xd9"

    throwaway = b""
    current = b""
    index = 0
    while current != MAGIC_BYTES:
        new_byte = sock.recv(1)
        if new_byte == b"":
            raise EOFError("Failed to recover from bad magic bytes")
        throwaway += new_byte
        if MAGIC_BYTES[index] == new_byte[0]:  # FIXME
            current += new_byte
            index += 1
        else:
            current = b""
            index = 0
    return throwaway


class Packet:
    def __init__(self, command, payload):
        self.command = command
        self.payload = payload

    @classmethod
    def from_socket(cls, sock):
        magic = read_magic(sock)
        if magic != NETWORK_MAGIC:
            throwaway = recover(sock)
            print(f"threw {len(throwaway)} bytes away ...")
            # raise RuntimeError("magic")

        command = read_command(sock)
        payload_length = read_length(sock)
        checksum = read_checksum(sock)
        payload = read_payload(sock, payload_length)

        computed_checksum = compute_checksum(payload)
        if computed_checksum != checksum:
            raise RuntimeError("Checksums don't match")

        if payload_length != len(payload):
            raise RuntimeError(
                "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

        return cls(command, payload)

    def to_bytes(self):
        result = int_to_bytes(NETWORK_MAGIC, 4)
        result += encode_command(self.command)
        result += int_to_bytes(len(self.payload), 4)
        result += compute_checksum(self.payload)
        result += self.payload
        return result

    def __str__(self):
        headers = ["Packet", ""]
        rows = [["command", fmt(self.command)], ["payload", fmt(self.payload)]]
        return tabulate(rows, headers, tablefmt="grid")

    def __repr__(self):
        return f"<Message command={self.command}>"


def handshake(address, log=True):
    # Arguments for our outgoing VersionMessage
    services = 1
    my_ip = "7.7.7.7"
    peer_ip = address[0]
    port = address[1]
    now = int(time.time())
    my_address = Address(services, my_ip, port, time=None)
    peer_address = Address(services, peer_ip, port, time=None)

    # Create out outgoing VersionMessage and Packet instances
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
    version_packet = Packet(
        command=version_message.command, payload=version_message.to_bytes()
    )
    serialized_packet = version_packet.to_bytes()

    # Create the socket
    sock = socket.socket()

    # Initiate TCP connection
    sock.connect(address)

    # Initiate the Bitcoin version handshake
    sock.send(serialized_packet)

    # Receive their "version" response
    pkt = Packet.from_socket(sock)
    peer_version_message = VersionMessage.from_bytes(pkt.payload)
    if log:
        print(peer_version_message)

    # Receive their "verack" response
    pkt = Packet.from_socket(sock)
    peer_verack_message = VerackMessage.from_bytes(pkt.payload)
    if log:
        print(peer_verack_message)

    # Send out "verack" response
    verack_message = VerackMessage()
    verack_packet = Packet(verack_message.command, payload=verack_message.to_bytes())
    sock.send(verack_packet.to_bytes())

    return sock
