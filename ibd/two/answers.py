############
# Lesson 1 #
############

# Exercise #1

def read_version(binary_stream):
    bytes_ = binary_stream.read(4)
    int_ = bytes_to_int(bytes_)
    return int_

# Exercise #2
# That 60001 is the cutoff can be found in the "hint" link

def can_send_pong(binary_stream):
    return read_version(binary_stream) >= 60001

# Exercise #3

def read_bool(stream):
    bytes_ = stream.read(1)
    if len(bytes_) != 1:
        raise RuntimeError("Stream ran dry")
    integer =  bytes_to_int(bytes_)
    boolean = bool(integer)
    return boolean

# Exercise #4

def read_var_int(stream):
    i = read_int(stream, 1)
    if i == 0xff:
        return bytes_to_int(stream.read(8))
    elif i == 0xfe:
        return bytes_to_int(stream.read(4))
    elif i == 0xfd:
        return bytes_to_int(stream.read(2))
    else:
        return

# Exercise #5

def read_var_str(stream):
    length = read_var_int(stream)
    string = stream.read(length)
    return string
    
# Exercise #6

def offers_node_network_service(services_bitfield):
    # given integer services_bitfield, return whether the NODE_NETWORK bit is on
    return services_int_to_dict(services_bitfield)['NODE_NETWORK']

def offers_node_bloom_and_node_witness_services(services_bitfield):
    # given integer services_bitfield, return whether the 
    # NODE_BLOOM and NODE_WITNESS bits are on
    return services_int_to_dict(services_bitfield)['NODE_BLOOM'] \
        and services_int_to_dict(services_bitfield)['NODE_WITNESS']
