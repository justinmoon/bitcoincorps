############
# Lesson 1 #
############

# Exercise #1

def read_int(stream, n, byte_order='little'):
    b = stream.read(n)
    return bytes_to_int(b, byte_order)

# Exercise #2

def read_version(stream):
    return read_int(stream, 4)

# Exercise #3
# That 60001 is the cutoff can be found in the "hint" link

def can_send_pong(stream):
    return read_version(stream) >= 60001

# Exercise #4

def read_bool(stream):
    integer = read_int(stream, 1)
    boolean = bool(integer)
    return boolean


# Exercise #5

def read_var_int(stream):
    i = read_int(stream, 1)
    if i == 0xff:
        return read_int(stream, 8)
    elif i == 0xfe:
        return read_int(stream, 4)
    elif i == 0xfd:
        return read_int(stream, 2)
    else:
        return i

# Exercise #5

def read_var_str(stream):
    length = read_var_int(stream)
    string = stream.read(length)
    return string
    
# Exercise #6

def read_var_str(stream):
    length = read_var_int(stream)
    string = stream.read(length)
    return string

# Exercise #7
def services_int_to_dict(services_int):
    return {
        'NODE_NETWORK': check_bit(services_int, 0),           # 1    = 2**0
        'NODE_GETUTXO': check_bit(services_int, 1),           # 2    = 2**1
        'NODE_BLOOM': check_bit(services_int, 2),             # 4    = 2**2
        'NODE_WITNESS': check_bit(services_int, 3),           # 8    = 2**3
        'NODE_NETWORK_LIMITED': check_bit(services_int, 10),  # 1024 = 2**10
    }

def read_services(stream):
    services_int = read_int(stream, 8)
    return services_int_to_dict(services_int)

# Exercise #8

def offers_node_network_service(services_bitfield):
    # given integer services_bitfield, return whether the NODE_NETWORK bit is on
    return services_int_to_dict(services_bitfield)['NODE_NETWORK']

def offers_node_bloom_and_node_witness_services(services_bitfield):
    # given integer services_bitfield, return whether the 
    # NODE_BLOOM and NODE_WITNESS bits are on
    return services_int_to_dict(services_bitfield)['NODE_BLOOM'] \
        and services_int_to_dict(services_bitfield)['NODE_WITNESS']

# Exercise #9

def read_ip(stream):
    bytes_ = stream.read(16)
    return ip_address(bytes_)

# Exercise #10

def read_port(stream):
    return read_int(stream, 2, byte_order="big")




