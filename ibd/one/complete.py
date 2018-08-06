from io import BytesIO
from hashlib import sha256
import re

from tabulate import tabulate

NETWORK_MAGIC = 0xD9B4BEF9


def fmt(bytestr):
    maxlen = 500
    msg = str(bytestr[:maxlen])
    if len(bytestr) > maxlen:
        msg += "..."
    return re.sub("(.{80})", "\\1\n", msg, 0, re.DOTALL)


def bytes_to_int(b, byte_order="little"):
    return int.from_bytes(b, byte_order)


def int_to_bytes(i, length, byte_order="little"):
    return int.to_bytes(i, length, byte_order)


def read_magic(sock):
    magic_bytes = sock.recv(4)
    magic = bytes_to_int(magic_bytes)
    return magic


def read_command(sock):
    raw = sock.recv(12)
    # remove empty bytes
    command = raw.replace(b"\x00", b"")
    return command


def read_length(sock):
    raw = sock.recv(4)
    length = bytes_to_int(raw)
    return length


def read_checksum(sock):
    # FIXME: protocol documentation says this should be an integer ...
    raw = sock.recv(4)
    return raw


def calculate_checksum(payload_bytes):
    first_round = sha256(payload_bytes).digest()
    second_round = sha256(first_round).digest()
    first_four_bytes = second_round[:4]
    return first_four_bytes


def read_payload(sock, length):
    payload = sock.recv(length)
    return payload


class FakeSocket:

    def __init__(self, bytes_):
        self.stream = BytesIO(bytes_)

    def recv(self, n):
        return self.stream.read(n)


# this used to be called "Message"
class Packet:
    def __init__(self, command, payload):
        self.command = command
        self.payload = payload

    @classmethod
    def from_socket(cls, sock):
        magic = read_magic(sock)
        if magic != NETWORK_MAGIC:
            raise RuntimeError(f'Network magic "{magic}" is wrong')

        command = read_command(sock)
        payload_length = read_length(sock)
        checksum = read_checksum(sock)
        payload = read_payload(sock, payload_length)

        calculated_checksum = calculate_checksum(payload)
        if calculated_checksum != checksum:
            raise RuntimeError("Checksums don't match")

        if payload_length != len(payload):
            raise RuntimeError(
                "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

        return cls(command, payload)

    def __str__(self):
        headers = ["Packet", ""]
        rows = [["command", fmt(self.command)], ["payload", fmt(self.payload)]]
        return tabulate(rows, headers, tablefmt="grid")

    def __repr__(self):
        return f"<Message command={self.command}>"
