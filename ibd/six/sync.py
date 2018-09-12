import io

from ibd.six.utils import int_to_bytes
from ibd.six.wire import Packet
from ibd.six.msg import GetHeaders, Headers, GetData, InventoryItem
from ibd.six.block import BlockLocator, Block
from ibd.six.wire import handshake

# just stores the integer representation of the headers
genesis = int("000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f", 16)
blocks = [genesis]


def construct_block_locator():
    step = 1
    height = len(blocks) - 1
    hashes = []

    while height >= 0:
        header = blocks[height]
        hashes.append(header)
        height -= step
        # step starts doubling after the 11th hash
        if len(hashes) > 10:
            step *= 2

    if not blocks.index(genesis):
        blocks.append(genesis)

    return BlockLocator(items=hashes)


def send_getheaders(sock):
    locator = construct_block_locator()
    getheaders = GetHeaders(locator)
    msg = Packet(getheaders.command, getheaders.to_bytes())
    sock.send(msg.to_bytes())
    print("sent getheaders")


def update_blocks(block_headers):
    for header in block_headers.headers:
        # this is naive ...
        # we add it to the blocks if prev_block is our current tip
        if header.prev_block == blocks[-1]:
            blocks.append(header.pow())
        else:
            break


# FIXME
def pretty(self):
    hx = hex(self)[2:]  # remove "0x" prefix
    sigfigs = len(hx)
    padding = "0" * (64 - sigfigs)
    return padding + hx


def handle_headers_packet(packet, sock):
    block_headers = Headers.from_stream(io.BytesIO(packet.payload))
    print(f"{len(block_headers.headers)} new headers")
    update_blocks(block_headers)

    # after 500 headers, get the blocks
    if len(blocks) < 5000:
        send_getheaders(sock)
    else:
        print([pretty(block) for block in blocks[:100]])
        items = [InventoryItem(2, int_to_bytes(hash_, 32)) for hash_ in blocks[:10]]
        getdata = GetData(items=items)
        packet = Packet(getdata.command, getdata.to_bytes())
        sock.send(packet.to_bytes())

    print(f"We now have {len(blocks)} headers")


def handle_block_packet(packet, sock):
    block = Block.from_stream(io.BytesIO(packet.payload))
    print(block)


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
    sock = handshake(address)
    send_getheaders(sock)
    while True:
        try:
            packet = Packet.from_socket(sock)
        except EOFError:
            print("Peer hung up")
            return
        except Exception as e:
            print(f'encountered "{e}" reading packet')
        handle_packet(packet, sock)


if __name__ == "__main__":
    main()
