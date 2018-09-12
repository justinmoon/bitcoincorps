import hashlib
import re
import socket


NETWORK_MAGIC = 0xD9B4BEF9
IPV4_PREFIX = b"\x00" * 10 + b"\xff" * 2


def double_sha256(b):
    first_round = hashlib.sha256(b).digest()
    second_round = hashlib.sha256(first_round).digest()
    return second_round


# FIXME
def fmt(bytestr):
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
