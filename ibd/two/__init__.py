import re
from datetime import datetime
from hashlib import sha256
from io import BytesIO

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


def read_version(binary_stream):
    bytes_ = binary_stream.read(4)
    int_ = bytes_to_int(bytes_)
    return int_


def read_int(stream, n, byte_order="little"):
    b = stream.read(n)
    return bytes_to_int(b, byte_order)


def read_bool(stream):
    bytes_ = stream.read(1)
    integer = bytes_to_int(bytes_)
    boolean = bool(integer)
    return boolean


def read_timestamp(stream):
    timestamp = read_int(stream, 8)
    return datetime.fromtimestamp(timestamp)


def read_var_int(stream):
    i = read_int(stream, 1)
    if i == 0xff:
        return bytes_to_int(stream.read(8))
    elif i == 0xfe:
        return bytes_to_int(stream.read(4))
    elif i == 0xfd:
        return bytes_to_int(stream.read(2))
    else:
        return i


def read_var_str(stream):
    length = read_var_int(stream)
    string = stream.read(length)
    return string


def check_bit(number, index):
    """See if the bit at `index` in binary representation of `number` is on"""
    mask = 1 << index
    return bool(number & mask)


def services_int_to_dict(services_int):
    return {
        "NODE_NETWORK": check_bit(services_int, 0),  # 1 = 2**0
        "NODE_GETUTXO": check_bit(services_int, 1),  # 2 = 2**1
        "NODE_BLOOM": check_bit(services_int, 2),  # 4 = 2**2
        "NODE_WITNESS": check_bit(services_int, 3),  # 8 = 2**3
        "NODE_NETWORK_LIMITED": check_bit(services_int, 10),  # 1024 = 2**10
    }


def read_services(stream):
    services_int = read_int(stream, 8)
    return services_int_to_dict(services_int)

def read_ip(stream):
    bytes_ = stream.read(16)
    return ip_address(bytes_)


def read_port(stream):
    return read_int(stream, 2, byte_order="big")

class Address:

    def __init__(self, services, ip, port, time):
        self.services = services
        self.ip = ip
        self.port = port
        self.time = time

    @classmethod
    def from_bytes(cls, bytes_, version_msg=False):
        stream = BytesIO(bytes_)
        return cls.from_stream(stream, version_msg)
    
    @classmethod
    def from_stream(cls, stream, version_msg=False):
        if version_msg:
            time = None
        else:
            time = read_timestamp(stream)
        services = read_services(stream)
        ip = stream.read(16)
        port = read_int(stream, 2, byte_order='big')
        return cls(services, ip, port, time)
    
    def __repr__(self):
        return f"<Address {self.ip}:{self.port}>"

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
