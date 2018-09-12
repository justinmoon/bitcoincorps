import io
from tabulate import tabulate
from six.utils import (
    read_var_int, read_time, read_services, read_ip, time_to_bytes,
    services_to_bytes, read_port, ip_to_bytes, port_to_bytes, read_int,
    read_var_str, read_bool, int_to_bytes, bool_to_bytes, str_to_var_str,
    fmt, bytes_to_int, int_to_var_int
)
from six.block import BlockHeader

inv_map = {
    0: "ERROR",
    1: "MSG_TX",
    2: "MSG_BLOCK",
    3: "MSG_FILTERED_BLOCK",
    4: "MSG_CMPCT_BLOCK",
}


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


class GetBlocks:

    command = b"getblocks"

    def __init__(self, locator, hashstop=0):
        self.locator = locator
        self.hashstop = hashstop

    def to_bytes(self):
        msg = self.locator.to_bytes()
        msg += int_to_bytes(self.hashstop, 32)
        return msg


class GetHeaders:

    command = b"getheaders"

    def __init__(self, locator, hashstop=0):
        self.locator = locator
        self.hashstop = hashstop

    def to_bytes(self):
        msg = self.locator.to_bytes()
        msg += int_to_bytes(self.hashstop, 32)
        return msg


class InventoryItem:
    def __init__(self, type_, hash_):
        self.type = type_
        self.hash = hash_

    @classmethod
    def from_stream(cls, s):
        type_ = bytes_to_int(s.read(4))
        hash_ = s.read(32)
        return cls(type_, hash_)

    def to_bytes(self):
        msg = b""
        msg += int_to_bytes(self.type, 4)
        msg += self.hash
        return msg

    def __repr__(self):
        return f"<InvItem {inv_map[self.type]} {self.hash}>"


class GetData:
    command = b"getdata"

    def __init__(self, items=None):
        if items is None:
            self.items = []
        else:
            self.items = items

    def to_bytes(self):
        msg = int_to_var_int(len(self.items))
        for item in self.items:
            msg += item.to_bytes()
        return msg

    def __repr__(self):
        return f"<Getdata {repr(self.inv)}>"


class Headers:

    command = b"headers"

    def __init__(self, count, headers):
        self.count = count
        self.headers = headers

    @classmethod
    def from_stream(cls, s):
        count = read_var_int(s)
        headers = []
        for _ in range(count):
            header = BlockHeader.from_stream(s)
            headers.append(header)
        return cls(count, headers)

    def __repr__(self):
        return f"<Headers #{len(self.headers)}>"
