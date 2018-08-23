class Pet:
    valid_kinds = [b"cat", b"dog", b"pig", b"cow"]
    
    def __init__(self, kind, name):
        self.kind = kind
        self.name = name
    
    @classmethod
    def from_bytes(cls, b):
        stream = io.BytesIO(b)
        kind = stream.read(3)
        if kind not in cls.valid_kinds:
            raise RuntimeError("invalid 'kind'")
        name = stream.read(10)
        return cls(kind, name)
    
    def to_bytes(self):
        return self.kind + self.name


def int_to_var_int(i):
    if i < 0xfd:
        return bytes([i])
    elif i <= 0xffff:
        return b"\xfd" + int_to_bytes(i, 2)
    elif i <= 0xffffffff:
        return b"\xfe" + int_to_bytes(i, 4)
    elif i <= 0xffffffffffffffff:
        return b"\xff" + int_to_bytes(i, 8)
    else:
        raise RuntimeError("integer too large: {}".format(i))

def bool_to_bytes(b): 
    i = int(b) # 0 or 1
    return int_to_bytes(i, 1)
