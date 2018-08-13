import re
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from ipaddress import ip_address

from tabulate import tabulate

NETWORK_MAGIC = 0xD9B4BEF9


def read_pkt_bytes(sock):
    magic = sock.read(4)
    if magic != NETWORK_MAGIC:
        raise RuntimeError(f'Network magic "{magic}" is wrong')
    command = sock.read(12)
    raw_length = sock.read(4)
    length = bytes_to_int(raw_length)
    checksum = sock.read(4)
    payload = sock.read(length)
    calculated_checksum = calculate_checksum(payload)
    if calculated_checksum != checksum:
        raise RuntimeError("Checksums don't match")
    if length != len(payload):
        raise RuntimeError(
            "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
        )
    return magic + command + raw_length + checksum + payload


def handshake():
    pass


def async_handshake(address):
    pass


def encode_command(cmd):
    padding_needed = 12 - len(cmd)
    padding = b"\x00" * padding_needed
    return cmd + padding


def fmt(bytestr):
    # FIXME
    string = str(bytestr)
    maxlen = 500
    msg = string[:maxlen]
    if len(string) > maxlen:
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
    payload = recv_n(sock, length)
    return payload


def read_int(stream, n, byte_order="little"):
    b = stream.read(n)
    return bytes_to_int(b, byte_order)


def read_version(stream):
    return read_int(stream, 4)


def read_bool(stream):
    integer = read_int(stream, 1)
    boolean = bool(integer)
    return boolean


def read_timestamp(stream, n):
    timestamp = read_int(stream, n)
    return datetime.fromtimestamp(timestamp)


def read_var_int(stream):
    i = read_int(stream, 1)
    if i == 0xff:
        return read_int(stream, 8)
    elif i == 0xfe:
        return read_int(stream, 4)
    elif i == 0xfd:
        return read_int(stream, 2)
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
            time = read_timestamp(stream, 4)
        services = read_services(stream)
        ip = read_ip(stream)
        port = read_port(stream)
        return cls(services, ip, port, time)

    def __repr__(self):
        return f"<Address {self.ip}:{self.port}>"


class AddrMessage:

    command = b"addr"

    def __init__(self, address_list):
        # FIXME this is kind of a weird variable name ...
        self.address_list = address_list

    @classmethod
    def from_bytes(cls, bytes_):
        stream = BytesIO(bytes_)
        count = read_var_int(stream)
        address_list = []
        for _ in range(count):
            address_list.append(Address.from_stream(stream))
        return cls(address_list)

    def __repr__(self):
        return f"<AddrMessage {len(self.address_list)}>"


class VersionMessage:

    command = b"version"

    def __init__(
        self,
        version,
        services,
        timestamp,
        addr_recv,
        addr_from,
        nonce,
        user_agent,
        start_height,
        relay,
    ):
        self.version = version
        self.services = services
        self.timestamp = timestamp
        self.addr_recv = addr_recv
        self.addr_from = addr_from
        self.nonce = nonce
        self.user_agent = user_agent
        self.start_height = start_height
        self.relay = relay

    @classmethod
    def from_bytes(cls, payload):
        stream = BytesIO(payload)
        version = read_int(stream, 4)
        services = read_services(stream)
        timestamp = read_timestamp(stream, 8)
        addr_recv = Address.from_stream(stream, version_msg=True)
        addr_from = Address.from_stream(stream, version_msg=True)
        nonce = read_int(stream, 8)
        user_agent = read_var_str(stream)
        start_height = read_int(stream, 4)
        relay = read_bool(stream)
        return cls(
            version,
            services,
            timestamp,
            addr_recv,
            addr_from,
            nonce,
            user_agent,
            start_height,
            relay,
        )

    def __str__(self):
        headers = ["VersionMessage", ""]
        attrs = [
            "version",
            "services",
            "timestamp",
            "addr_recv",
            "addr_from",
            "nonce",
            "user_agent",
            "start_height",
            "relay",
        ]
        rows = [[attr, fmt(getattr(self, attr))] for attr in attrs]
        return tabulate(rows, headers, tablefmt="grid")

    def __repr__(self):
        return f"<Message command={self.command}>"


class VerackMessage:

    command = b"verack"

    @classmethod
    def from_bytes(cls, s):
        return cls()

    def to_bytes(self):
        return b""


async def async_read_magic(sock):
    magic_bytes = await sock.recv(4)
    magic = bytes_to_int(magic_bytes)
    return magic


async def async_read_command(sock):
    raw = await sock.recv(12)
    # remove empty bytes
    command = raw.replace(b"\x00", b"")
    return command


async def async_read_length(sock):
    raw = await sock.recv(4)
    length = bytes_to_int(raw)
    return length


async def async_read_checksum(sock):
    # FIXME: protocol documentation says this should be an integer ...
    raw = await sock.recv(4)
    return raw


async def async_recv_n(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = b""
    while len(data) < n:
        packet = await sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def recv_n(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


async def async_read_payload(sock, length):
    payload = await async_recv_n(sock, length)
    return payload


async def async_read_message(sock):
    magic = await async_read_magic(sock)
    command = await async_read_command(sock)
    length = await async_read_length(sock)
    checksum = await async_read_checksum(sock)
    payload = await async_read_payload(sock, length)
    return magic + command + length + checksum + payload


def read_message(sock):
    magic = read_magic(sock)
    command = read_command(sock)
    length = read_length(sock)
    checksum = read_checksum(sock)
    payload = read_payload(sock, length)
    return magic + command + length + checksum + payload


MAGIC_BYTES = b"\xf9\xbe\xb4\xd9"


async def async_recover(sock):
    throwaway = b""
    current = b""
    index = 0
    while current != MAGIC_BYTES:
        new_byte = await sock.recv(1)
        throwaway += new_byte
        if MAGIC_BYTES[index] == new_byte[0]:  # FIXME
            current += new_byte
            index += 1
        else:
            current = b""
            index = 0
    return throwaway


def recover(sock):
    throwaway = b""
    current = b""
    index = 0
    while current != MAGIC_BYTES:
        new_byte = sock.recv(1)
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
            print(f"Incorrect network magic")
            throwaway = recover(sock)
            print(f"Throwing away {len(throwaway)} bytes:")
            print(throwaway)

        command = read_command(sock)
        payload_length = read_length(sock)
        checksum = read_checksum(sock)
        payload = read_payload(sock, payload_length)

        if payload_length != len(payload):
            raise RuntimeError(
                f"Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

        calculated_checksum = calculate_checksum(payload)
        if calculated_checksum != checksum:
            raise RuntimeError(f"Checksums don't match on {command}")

        return cls(command, payload)

    @classmethod
    async def async_from_socket(cls, sock):
        magic = await async_read_magic(sock)

        if magic != NETWORK_MAGIC:
            print(f"Incorrect network magic")
            throwaway = await async_recover(sock)
            print(f"Throwing away {len(throwaway)} bytes:")
            print(throwaway)
            # raise RuntimeError(f'Network magic "{magic}" is wrong')

        command = await async_read_command(sock)
        payload_length = await async_read_length(sock)
        checksum = await async_read_checksum(sock)
        payload = await async_read_payload(sock, payload_length)

        if payload_length != len(payload):
            raise RuntimeError(
                f"Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

        calculated_checksum = calculate_checksum(payload)
        if calculated_checksum != checksum:
            raise RuntimeError(f"Checksums don't match on {command}")

        return cls(command, payload)

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
            raise RuntimeError(f"Checksums don't match on {command}")

        if payload_length != len(payload):
            raise RuntimeError(
                "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

        return cls(command, payload)

    def to_bytes(self):
        result = int_to_bytes(NETWORK_MAGIC, 4)  # FIXME
        result += encode_command(self.command)
        result += int_to_bytes(len(self.payload), 4)
        result += calculate_checksum(self.payload)[:4]
        result += self.payload
        return result

    def __str__(self):
        headers = ["Packet", ""]
        rows = [["command", fmt(self.command)], ["payload", fmt(self.payload)]]
        return tabulate(rows, headers, tablefmt="grid")

    def __repr__(self):
        return f"<Message command={self.command}>"
