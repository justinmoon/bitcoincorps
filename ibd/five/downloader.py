from ibd.three.complete import *
from ibd.three.handshake import handshake


def double_sha256(b):
    first_round = hashlib.sha256(b).digest()
    second_round = hashlib.sha256(first_round).digest()
    return second_round


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


class BlockLocator:
    def __init__(self, items=None, version=70015):
        # self.items is a list of block hashes ... not sure on data type
        if items:
            self.items = items
        else:
            self.items = []
        self.version = version

    def to_bytes(self):
        msg = int_to_bytes(self.version, 4)
        msg += int_to_var_int(len(self.items))
        for hash_ in self.items:
            msg += int_to_bytes(hash_, 32)
        return msg


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


class BlockHeader:
    def __init__(
        self, version, prev_block, merkle_root, timestamp, bits, nonce, txn_count
    ):
        self.version = version
        self.prev_block = prev_block
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.bits = bits
        self.nonce = nonce
        self.txn_count = txn_count

    @classmethod
    def from_stream(cls, s):
        version = bytes_to_int(s.read(4))
        # prev_block = s.read(32)[::-1]  # little endian
        prev_block = bytes_to_int(s.read(32))
        # merkle_root = s.read(32)[::-1]  # little endian
        merkle_root = bytes_to_int(s.read(32))
        timestamp = bytes_to_int(s.read(4))
        bits = s.read(4)
        nonce = s.read(4)
        txn_count = read_var_int(s)  # apparently this is always 0?
        return cls(version, prev_block, merkle_root, timestamp, bits, nonce, txn_count)

    def to_bytes(self):
        # version - 4 bytes, little endian
        result = int_to_bytes(self.version, 4)
        # prev_block - 32 bytes, little endian
        result += int_to_bytes(self.prev_block, 32)
        # merkle_root - 32 bytes, little endian
        result += int_to_bytes(self.merkle_root, 32)
        # timestamp - 4 bytes, little endian
        result += int_to_bytes(self.timestamp, 4)
        # bits - 4 bytes
        result += self.bits
        # nonce - 4 bytes
        result += self.nonce
        return result

    def hash(self):
        """Returns the double-sha256 interpreted little endian of the block"""
        # to_bytes
        s = self.to_bytes()
        # double-sha256
        sha = double_sha256(s)
        # reverse
        return sha[::-1]

    def pow(self):
        s = self.to_bytes()
        sha = double_sha256(s)
        return bytes_to_int(sha)

    def target(self):
        """Returns the proof-of-work target based on the bits"""
        # last byte is exponent
        exponent = self.bits[-1]
        # the first three bytes are the coefficient in little endian
        coefficient = bytes_to_int(self.bits[:-1])
        # the formula is:
        # coefficient * 2**(8*(exponent-3))
        return coefficient * 2 ** (8 * (exponent - 3))

    def check_pow(self):
        """Returns whether this block satisfies proof of work"""
        return self.pow() < self.target()

    def pretty(self):
        hx = hex(self.pow())[2:]  # remove "0x" prefix
        sigfigs = len(hx)
        padding = "0" * (64 - sigfigs)
        return padding + hx

    def __repr__(self):
        return f"<Header merkle_root={self.merkle_root}>"


class Block(BlockHeader):
    def __init__(
        self, version, prev_block, merkle_root, timestamp, bits, nonce, txn_count, txns
    ):
        super().__init__(
            version, prev_block, merkle_root, timestamp, bits, nonce, txn_count
        )
        self.txns = txns

    @classmethod
    def from_stream(cls, s):
        version = bytes_to_int(s.read(4))
        # prev_block = s.read(32)[::-1]  # little endian
        prev_block = bytes_to_int(s.read(32))
        # merkle_root = s.read(32)[::-1]  # little endian
        merkle_root = bytes_to_int(s.read(32))
        timestamp = bytes_to_int(s.read(4))
        bits = s.read(4)
        nonce = s.read(4)
        txn_count = read_var_int(s)  # apparently this is always 0?
        txns = [Tx.from_stream(s) for _ in range(txn_count)]
        return cls(
            version, prev_block, merkle_root, timestamp, bits, nonce, txn_count, txns
        )

    def __repr__(self):
        return f"<Block merkle_root={self.merkle_root} | {len(self.txns)} txns>"


class Tx:
    def __init__(self, version, tx_ins, tx_outs, locktime, testnet=False):
        self.version = version
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs
        self.locktime = locktime
        self.testnet = testnet

    @classmethod
    def from_stream(cls, s):
        """Takes a byte stream and from_streams the transaction at the start
        return a Tx object
        """
        # s.read(n) will return n bytes
        # version has 4 bytes, little-endian, interpret as int
        version = bytes_to_int(s.read(4))
        # num_inputs is a varint, use read_var_int(s)
        num_inputs = read_var_int(s)
        # each input needs parsing
        inputs = []
        for _ in range(num_inputs):
            inputs.append(TxIn.from_stream(s))
        # num_outputs is a varint, use read_var_int(s)
        num_outputs = read_var_int(s)
        # each output needs parsing
        outputs = []
        for _ in range(num_outputs):
            outputs.append(TxOut.from_stream(s))
        # locktime is 4 bytes, little-endian
        locktime = bytes_to_int(s.read(4))
        # return an instance of the class (cls(...))
        return cls(version, inputs, outputs, locktime)

    def __repr__(self):
        return "<Tx version: {} ntx_ins: {} tx_outs: {} nlocktime: {}>".format(
            self.version,
            ",".join([repr(t) for t in self.tx_ins]),
            ",".join([repr(t) for t in self.tx_outs]),
            self.locktime,
        )


class TxIn:
    def __init__(self, prev_tx, prev_index, script_sig, sequence):
        self.prev_tx = prev_tx
        self.prev_index = prev_index
        self.script_sig = script_sig  # TODO from_stream it
        self.sequence = sequence

    def __repr__(self):
        return "<TxIn {}:{}>".format(self.prev_tx.hex(), self.prev_index)

    @classmethod
    def from_stream(cls, s):
        """Takes a byte stream and from_streams the tx_input at the start
        return a TxIn object
        """
        # s.read(n) will return n bytes
        # prev_tx is 32 bytes, little endian
        prev_tx = s.read(32)[::-1]
        # prev_index is 4 bytes, little endian, interpret as int
        prev_index = bytes_to_int(s.read(4))
        # script_sig is a variable field (length followed by the data)
        # get the length by using read_var_int(s)
        script_sig_length = read_var_int(s)
        script_sig = s.read(script_sig_length)
        # sequence is 4 bytes, little-endian, interpret as int
        sequence = bytes_to_int(s.read(4))
        # return an instance of the class (cls(...))
        return cls(prev_tx, prev_index, script_sig, sequence)


class TxOut:
    def __init__(self, amount, script_pubkey):
        self.amount = amount
        self.script_pubkey = script_pubkey  # TODO from_stream it

    def __repr__(self):
        return "<TxOut {}:{}>".format(self.amount, self.script_pubkey)

    @classmethod
    def from_stream(cls, s):
        """Takes a byte stream and from_streams the tx_output at the start
        return a TxOut object
        """
        # s.read(n) will return n bytes
        # amount is 8 bytes, little endian, interpret as int
        amount = bytes_to_int(s.read(8))
        # script_pubkey is a variable field (length followed by the data)
        # get the length by using read_var_int(s)
        script_pubkey_length = read_var_int(s)
        script_pubkey = s.read(script_pubkey_length)
        # return an instance of the class (cls(...))
        return cls(amount, script_pubkey)


# just stores the integer representation of the headers
genesis = int("00000000000000000013424801fbec52484d7211c223beec97f02236a9b6ee03", 16)
blocks = [genesis]


def construct_block_locator():
    step = 1
    height = len(blocks) - 1
    hashes = []

    while height >= 0:
        if len(hashes) >= 10:
            step *= 2
        header = blocks[height]
        hashes.append(header)
        height -= step

    if not blocks.index(genesis):
        blocks.append(genesis)

    return BlockLocator(items=hashes)


def send_getheaders(sock):
    locator = construct_block_locator()
    getheaders = GetHeaders(locator)
    msg = Packet(getheaders.command, getheaders.to_bytes())
    sock.send(msg.to_bytes())
    print("sent getheaders")


def handle_packet(packet):
    print(f'received "{packet.command}"')


def main():
    address = ("91.221.70.137", 8333)
    sock = handshake(address)
    send_getheaders(sock)
    while True:
        try:
            packet = Packet.from_socket(sock)
        except Exception as e:
            print(f'encountered "{e}" while new packet')
        handle_packet(packet)


if __name__ == "__main__":
    main()
