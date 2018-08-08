from ibd.two.complete import *


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
    if payload_length != len(payload):
        raise RuntimeError(
            "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
        )
    return magic + command + raw_length + checksum + payload


def handshake():
    pass
