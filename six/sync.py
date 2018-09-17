import io
import socket


from helper import int_to_little_endian, little_endian_to_int
from network import VersionMessage, HeadersMessage, NetworkEnvelope, GetHeaders, GetData, InventoryItem, BlockHeaderLocator
from block import BlockHeader, Block


# just stores the integer representation of the headers
genesis_hash = int("000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f", 16)
genesis_raw = b"\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xffM\x04\xff\xff\x00\x1d\x01\x04EThe Times 03/Jan/2009 Chancellor on brink of second bailout for banks\xff\xff\xff\xff\x01\x00\xf2\x05*\x01\x00\x00\x00CA\x04g\x8a\xfd\xb0\xfeUH'\x19g\xf1\xa6q0\xb7\x10\\\xd6\xa8(\xe09\t\xa6yb\xe0\xea\x1fa\xde\xb6I\xf6\xbc?L\xef8\xc4\xf3U\x04\xe5\x1e\xc1\x12\xde\\8M\xf7\xba\x0b\x8dW\x8aLp+k\xf1\x1d_\xac\x00\x00\x00\x00"

# genesis_block = Block.parse(io.BytesIO(genesis_raw))
data = {
    "headers": [genesis_hash],
    "blocks": [],
}


def handshake(address):
    # Create the socket
    sock = socket.socket()
    stream = sock.makefile('rb', None)
    # Initiate TCP connection
    sock.connect(address)

    # Send our "version" message
    payload = VersionMessage().serialize()
    envelope = NetworkEnvelope(command=b"version", payload=payload)
    sock.send(envelope.serialize())

    # Receive peer's "version" message
    envelope = NetworkEnvelope.parse(stream)
    print(envelope.command)

    # Receive peer's "verack" message
    envelope = NetworkEnvelope.parse(stream)
    print(envelope.command)

    # Send our "verack" message
    envelope = NetworkEnvelope(command=b"verack", payload=b"")
    sock.send(envelope.serialize())

    return sock, stream


def construct_block_locator():
    step = 1
    height = len(data["headers"]) - 1
    hashes = []

    while height >= 0:
        header = data["headers"][height]
        hashes.append(header)
        height -= step
        # step starts doubling after the 11th hash
        if len(hashes) > 10:
            step *= 2

    if not hashes.index(genesis_hash):
        hashes.append(genesis_hash)

    return BlockHeaderLocator(items=hashes)


def send_getheaders(sock):
    locator = construct_block_locator()
    getheaders = GetHeaders(locator)
    msg = NetworkEnvelope(getheaders.command, getheaders.serialize())
    sock.send(msg.serialize())
    print("sent getheaders")


def persist_headers(headers):
    for block in headers:
        # this is naive ...
        # we add it to the blocks if prev_block is our current tip
        if int.from_bytes(block.prev_block, 'big') == data["headers"][-1]:
            data["headers"].append(block.proof())
        else:
            print("out of order")
            break


def get_blocks(sock):
    index = len(data["blocks"])
    items = [InventoryItem(2, int_to_little_endian(hash_, 32))
             for hash_ in data["headers"][index:index+10]]
    getdata = GetData(items=items)
    packet = NetworkEnvelope(getdata.command, getdata.serialize())
    sock.send(packet.serialize())


def handle_headers_packet(packet, sock):
    msg = HeadersMessage.parse(io.BytesIO(packet.payload))
    print(f"{len(msg.blocks)} new headers")
    persist_headers(msg.blocks)

    # after 1000 headers, get the blocks
    if len(data["headers"]) < 1000:
        send_getheaders(sock)
    else:
        get_blocks(sock)

    print(f"We now have {len(data['headers'])} headers")


def handle_block_packet(packet, sock):
    block = Block.parse(io.BytesIO(packet.payload))
    print("received", block)
    # FIXME
    if len(data["blocks"]) == 0:
        data["blocks"].append(block)
    if int.from_bytes(block.prev_block, 'big') == data["blocks"][-1].proof():
        data["blocks"].append(block)
    if len(data["blocks"]) % 10 == 0:
        get_blocks(sock)
    print(f"we now have {len(data['blocks'])} blocks")


def handle_packet(packet, sock):
    command_to_handler = {
        b"headers": handle_headers_packet,
        b"block": handle_block_packet,
    }
    handler = command_to_handler.get(packet.command)
    if handler:
        print(f'handling "{packet.command}"')
        handler(packet, sock)
    else:
        print(f'discarding "{packet.command}"')


def main():
    address = ("91.221.70.137", 8333)
    sock, stream = handshake(address)
    send_getheaders(sock)
    while True:
        try:
            packet = NetworkEnvelope.parse(stream)
        except EOFError:
            print("Peer hung up")
            return
        except Exception as e:
            print(f'encountered "{e}" reading packet')
        handle_packet(packet, sock)


if __name__ == "__main__":
    main()
