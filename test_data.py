import io

def int_to_bytes(n, length):
    return n.to_bytes(length, 'little')

def encode_var_int(i):
    if i < 0xfd:
        return bytes([i])
    elif i < 2 ** (8 * 2):
        return b'\xfd' + int_to_bytes(i, 2)
    elif i < 2 ** (8 * 4) - 1:
        return b'\xfe' + int_to_bytes(i, 4)
    elif i < 2 ** (8 * 8) - 1:
        return b'\xff' + int_to_bytes(i, 8)
    else:
        raise RuntimeError('integer too large: {}'.format(i))


def read_var_str(s):
    length = read_var_int(s)
    string = s.read(length)
    return string


def encode_var_str(s):
    length = len(s)
    return encode_var_int(length) + s


version_numbers = [
    70015,
    60001,
    106,
]

version_number_bytes = [i.to_bytes(4, 'little') for i in version_numbers]

version_byte_strings =[ 
    version_number_bytes[0] + b'\r\x04\x00\x00\x00\x00\x00\x003\xc2X[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{\xc5\xa7\x80\xa1\x87\xc1\xda\x10/Satoshi:0.16.0/\x8d$\x08\x00\x01',

    version_number_bytes[1] + b'\r\x04\x00\x00\x00\x00\x00\x003\xc2X[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{\xc5\xa7\x80\xa1\x87\xc1\xda\x10/Satoshi:0.16.0/\x8d$\x08\x00\x01',

    version_number_bytes[2] + b'\r\x04\x00\x00\x00\x00\x00\x003\xc2X[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00{\xc5\xa7\x80\xa1\x87\xc1\xda\x10/Satoshi:0.16.0/\x8d$\x08\x00\x01',
]

def make_version_streams():
    return [io.BytesIO(b) for b in version_byte_strings]

true_bytes = (True).to_bytes(1, 'little')
false_bytes = (False).to_bytes(1, 'little')

def make_stream(bytes_):
    return io.BytesIO(bytes_)

eight_byte_int = 2 ** (8 * 8) - 1
four_byte_int = 2 ** (8 * 4) - 1
two_byte_int = 2 ** (8 * 2) - 1
one_byte_int = 7

eight_byte_int_bytes = eight_byte_int.to_bytes(8, 'little')
four_byte_int_bytes = four_byte_int.to_bytes(4, 'little')
two_byte_int_bytes = two_byte_int.to_bytes(2, 'little')
one_byte_int_bytes = one_byte_int.to_bytes(1, 'little')

eight_byte_prefix = (0xff).to_bytes(1, 'little')
four_byte_prefix = (0xfe).to_bytes(1, 'little')
two_byte_prefix = (0xfd).to_bytes(1, 'little')

eight_byte_var_int =  eight_byte_prefix + eight_byte_int_bytes
four_byte_var_int = four_byte_prefix + four_byte_int_bytes
two_byte_var_int = two_byte_prefix + two_byte_int_bytes
one_byte_var_int = one_byte_int_bytes


long_str = b"A purely peer-to-peer version of electronic cash would allow online payments to be sent directly from one party to another without going through a financial institution. Digital signatures provide part of the solution, but the main benefits are lost if a trusted third party is still required to prevent double-spending. We propose a solution to the double-spending problem using a peer-to-peer network.  The network timestamps transactions by hashing them into an ongoing chain of hash-based proof-of-work, forming a record that cannot be changed without redoing the proof-of-work. The longest chain not only serves as proof of the sequence of events witnessed, but proof that it came from the largest pool of CPU power. As long as a majority of CPU power is controlled by nodes that are not cooperating to attack the network, they'll generate the longest chain and outpace attackers. The network itself requires minimal structure. Messages are broadcast on a best effort basis, and nodes can leave and rejoin the network at will, accepting the longest proof-of-work chain as proof of what happened while they were gone."
long_var_str = encode_var_str(long_str)

short_str = b"!"
short_var_str = encode_var_str(short_str)
