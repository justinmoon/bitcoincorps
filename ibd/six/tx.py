from six.utils import (
    bytes_to_int, read_var_int,
)


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
