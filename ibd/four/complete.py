from ibd.two.complete import *


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


async def async_read_payload(sock, length):
    payload = await sock.recv(length)
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

    @classmethod
    async def async_from_socket(cls, sock):
        magic = await async_read_magic(sock)

        if magic != NETWORK_MAGIC:
            raise RuntimeError(f'Network magic "{magic}" is wrong')

        command = await async_read_command(sock)
        payload_length = await async_read_length(sock)
        checksum = await async_read_checksum(sock)
        payload = await async_read_payload(sock, payload_length)

        calculated_checksum = calculate_checksum(payload)
        if calculated_checksum != checksum:
            raise RuntimeError("Checksums don't match")

        if payload_length != len(payload):
            raise RuntimeError(
                "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
            )

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
