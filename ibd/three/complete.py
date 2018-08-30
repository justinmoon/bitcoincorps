import hashlib
import io
import re
import socket

from tabulate import tabulate

NETWORK_MAGIC = 0xD9B4BEF9
#
IPV4_PREFIX = b"\x00" * 10 + b"\xff" * 2


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


def read_int(stream, n, byte_order="little"):
    b = stream.read(n)
    return bytes_to_int(b, byte_order)


def read_magic(sock):
    magic_bytes = sock.recv(4)
    magic = bytes_to_int(magic_bytes)
    return magic


def read_command(sock):
    raw = sock.recv(12)
    # remove empty bytes
    command = raw.replace(b"\x00", b"")
    return command


def encode_command(cmd):
    padding_needed = 12 - len(cmd)
    padding = b"\x00" * padding_needed
    return cmd + padding


def read_length(sock):
    raw = sock.recv(4)
    length = bytes_to_int(raw)
    return length


def read_checksum(sock):
    # FIXME: protocol documentation says this should be an integer
    # But it's just easier to keep it as bytes
    raw = sock.recv(4)
    return raw


def compute_checksum(payload_bytes):
    first_round = hashlib.sha256(payload_bytes).digest()
    second_round = hashlib.sha256(first_round).digest()
    first_four_bytes = second_round[:4]
    return first_four_bytes


def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def read_payload(sock, length):
    payload = recvall(sock, length)
    return payload


def read_version(stream):
    return read_int(stream, 4)


def read_bool(stream):
    integer = read_int(stream, 1)
    boolean = bool(integer)
    return boolean


def read_time(stream, version_msg=True):
    # FIXME `version_message` probably not best name for this flag
    # FIXME: default true is also weird ...
    if version_msg:
        t = read_int(stream, 8)
    else:
        t = read_int(stream, 4)
    return t


def time_to_bytes(time, n):
    return int_to_bytes(time, n)


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


def int_to_var_int(i):
    """encodes an integer as a varint"""
    if i < 0xfd:
        return bytes([i])
    elif i < 0x10000:
        return b"\xfd" + int_to_bytes(i, 2)
    elif i < 0x100000000:
        return b"\xfe" + int_to_bytes(i, 4)
    elif i < 0x10000000000000000:
        return b"\xff" + int_to_bytes(i, 8)
    else:
        raise RuntimeError("integer too large: {}".format(i))


def str_to_var_str(s):
    # FIXME this actually takes bytes as argument ... confusing API
    length = len(s)
    return int_to_var_int(length) + s


def check_bit(number, index):
    """See if the bit at `index` in binary representation of `number` is on"""
    mask = 1 << index
    return bool(number & mask)


def lookup_services_key(services, key):
    key_to_bit = {
        "NODE_NETWORK": 0,  # 1 = 2**0
        "NODE_GETUTXO": 1,  # 2 = 2**1
        "NODE_BLOOM": 2,  # 4 = 2**2
        "NODE_WITNESS": 3,  # 8 = 2**3
        "NODE_NETWORK_LIMITED": 10,  # 1024 = 2**10
    }
    bit = key_to_bit[key]
    return check_bit(services, bit)


def services_to_bytes(services):
    return int_to_bytes(services, 8)


def read_services(stream):
    return read_int(stream, 8)


def read_port(stream):
    return read_int(stream, 2, byte_order="big")


def port_to_bytes(port):
    return int_to_bytes(port, 2, byte_order="big")


def bool_to_bytes(boolean):
    return int_to_bytes(int(boolean), 1)


def bytes_to_ip(b):
    if bytes(b[0:12]) == IPV4_PREFIX:  # IPv4
        return socket.inet_ntop(socket.AF_INET, b[12:16])
    else:  # IPv6
        return socket.inet_ntop(socket.AF_INET6, b)


def ip_to_bytes(ip):
    if ":" in ip:  # determine if address is IPv6
        return socket.inet_pton(socket.AF_INET6, ip)
    else:
        return IPV4_PREFIX + socket.inet_pton(socket.AF_INET, ip)


def read_ip(stream):
    bytes_ = stream.read(16)
    return bytes_to_ip(bytes_)


class AddrMessage:

    command = b"addr"

    def __init__(self, addresses):
        # FIXME this is kind of a weird variable name ...
        self.addresses = addresses

    @classmethod
    def from_bytes(cls, bytes_):
        stream = io.BytesIO(bytes_)
        count = read_var_int(stream)
        address_list = []
        for _ in range(count):
            address_list.append(Address.from_stream(stream))
        return cls(address_list)

    def __repr__(self):
        return f"<AddrMessage {len(self.address_list)}>"


class Address:
    def __init__(self, services, ip, port, time, id_=None):
        self.services = services
        self.ip = ip
        self.port = port
        self.time = time
        self.id = id_

    @classmethod
    def from_bytes(cls, bytes_, version_msg=False):
        stream = io.BytesIO(bytes_)
        return cls.from_stream(stream, version_msg)

    @classmethod
    def from_stream(cls, stream, version_msg=False):
        if version_msg:
            time = None
        else:
            time = read_time(stream, version_msg=version_msg)
        services = read_services(stream)
        ip = read_ip(stream)
        port = read_port(stream)
        return cls(services, ip, port, time)

    def to_bytes(self, version_msg=False):
        # FIXME: don't call this msg
        msg = b""
        # FIXME: What's the right condition here
        if self.time:
            msg += time_to_bytes(self.time, 4)
        msg += services_to_bytes(self.services)
        msg += ip_to_bytes(self.ip)
        msg += port_to_bytes(self.port)
        return msg

    def tuple(self):
        return (self.ip, self.port)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return f"<Address {self.ip}:{self.port}>"


class VersionMessage:

    command = b"version"

    def __init__(
        self,
        version,
        services,
        time,
        addr_recv,
        addr_from,
        nonce,
        user_agent,
        start_height,
        relay,
    ):
        self.version = version
        self.services = services
        self.time = time
        self.addr_recv = addr_recv
        self.addr_from = addr_from
        self.nonce = nonce
        self.user_agent = user_agent
        self.start_height = start_height
        self.relay = relay

    @classmethod
    def from_bytes(cls, payload):
        stream = io.BytesIO(payload)
        version = read_int(stream, 4)
        services = read_services(stream)
        time = read_time(stream)
        addr_recv = Address.from_stream(stream, version_msg=True)
        addr_from = Address.from_stream(stream, version_msg=True)
        nonce = read_int(stream, 8)
        user_agent = read_var_str(stream)
        start_height = read_int(stream, 4)
        relay = read_bool(stream)
        return cls(
            version,
            services,
            time,
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
            "time",
            "addr_recv",
            "addr_from",
            "nonce",
            "user_agent",
            "start_height",
            "relay",
        ]
        rows = [[attr, fmt(getattr(self, attr))] for attr in attrs]
        return tabulate(rows, headers, tablefmt="grid")

    def to_bytes(self):
        msg = int_to_bytes(self.version, 4)
        msg += services_to_bytes(self.services)
        msg += time_to_bytes(self.time, 8)
        msg += self.addr_recv.to_bytes()
        msg += self.addr_from.to_bytes()
        msg += int_to_bytes(self.nonce, 8)
        msg += str_to_var_str(self.user_agent)
        msg += int_to_bytes(self.start_height, 4)
        msg += bool_to_bytes(self.relay)
        return msg

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return f"<Message command={self.command}>"


class VerackMessage:

    command = b"verack"

    @classmethod
    def from_bytes(cls, s):
        return cls()

    def to_bytes(self):
        return b""

    def __str__(self):
        headers = ["VerackMessage", ""]
        rows = []
        return tabulate(rows, headers, tablefmt="grid")

    def __repr__(self):
        return "<Verack>"


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
