import socket
import os
import sys
import asyncio
import random
import requests

from library import Packet, VersionMessage, calculate_checksum, bytes_to_int

# FIXME: overwriting import
NETWORK_MAGIC = b"\xf9\xbe\xb4\xd9"

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


pkts = []
succeeded = 0
failed = 0
total = 0


def get_nodes():
    url = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    response = requests.get(url)
    return response.json()["nodes"]


def nodes_to_addr_tuples(nodes):
    raw_addrs = nodes.keys()
    addr_tuples = []
    for raw_addr in raw_addrs:
        ip, port = raw_addr.rsplit(":", 1)
        addr_tuple = (ip, int(port))
        addr_tuples.append(addr_tuple)
    return addr_tuples


def get_addr_tuples():
    nodes = get_nodes()
    return nodes_to_addr_tuples(nodes)


def connect_many(addrs):
    global succeeded, failed, pkts, total
    total = len(addrs)

    for addr_tuple in addrs:

        sock = socket.socket()
        sock.settimeout(1)

        try:
            sock.connect(addr_tuple)
            sock.send(VERSION)
            pkt = Packet.from_socket(sock)
            ver_pkt = VersionMessage.from_bytes(pkt.payload)
            # print(ver_pkt)
        except Exception as e:
            # print(e)
            failed += 1

        succeeded += 1
        print(f"{succeeded} / {total} tasks succeeded ({failed} failed)")
        sock.close()


def write_payloads(packets):
    with open("versions.txt", "ba") as f:
        for packet in packets:
            f.write(packet.payload + b"\n")


def cleanup():
    global succeeded, failed, pkts, total
    pkts = []
    succeeded = failed = total = 0

    try:
        os.remove("versions.txt")
    except FileNotFoundError:
        return


async def read_pkt(reader, host):
    magic = await reader.read(4)
    if magic != NETWORK_MAGIC:
        raise RuntimeError(f'Network magic "{magic}" is wrong')
    command = await reader.read(12)
    payload_length = bytes_to_int(await reader.read(4))
    checksum = await reader.read(4)
    payload = await reader.read(payload_length)
    if calculate_checksum(payload) != checksum:
        raise RuntimeError("Checksums don't match")
    if payload_length != len(payload):
        raise RuntimeError(
            "Tried to read {payload_length} bytes, only received {len(payload)} bytes"
        )
    return Packet(command, payload)


async def connect(host, port, index):
    global succeeded, failed, pkts, total

    # don't do everything at once ...
    await asyncio.sleep(random.random() * 10)

    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(VERSION)
        pkt = await read_pkt(reader, host)
    except Exception as e:
        #print(e)
        failed += 1
        return
    writer.close()

    succeeded += 1
    pkts.append(pkt)
    if succeeded % 500 == 0:
        print(f"{succeeded} / {total} tasks succeeded ({failed} failed)")
        write_payloads(pkts)
        pkts = []


def async_connect_many(addrs):
    global total
    total = len(addrs)
    tasks = [asyncio.create_task(connect(ip, port, index)) for index, (ip, port) in enumerate(addrs)]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))


if __name__ == "__main__":
    try:
        arg = sys.argv[1]
    except:
        arg = None

    cleanup()
    addrs = get_addr_tuples()


    if arg == "sync":
        connect_many(addrs)
    elif arg == "async":
        async_connect_many(addrs)
    else:
        print("Usage: \"python downloader.py <'sync' or 'async'>\"")
