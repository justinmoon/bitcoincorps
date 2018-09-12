from six.utils import (
    int_to_bytes, bytes_to_int, int_to_var_int, read_var_int, double_sha256
)
from six.tx import Tx


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
        return f"<Block {self.pretty()} >"
