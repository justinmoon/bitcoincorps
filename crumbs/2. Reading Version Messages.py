
# coding: utf-8

# # Reading Version Messages
# 
# In the last lesson we encountered the Bitcoin protocol's [Version Handshake](https://en.bitcoin.it/wiki/Version_Handshake). We saw how Bitcoin network peers won't respond if you don't start the conversion with a `version` message.
# 
# But _we cheated_. I gave you a serialized `version` message and didn't tell you how I created it.
# 
# _We were lazy_: we didn't parse the cryptic `payload` of the `version` message that our peer sent us.
# 
# _We were rude_! After listening for our peer's `version` message we stopped listening and never received or responded to their `verack` message -- completing the handshake. Our peer was left hanging ...
# 
# So you see, we have much to fix!
# 
# ### Housekeeping
# 
# In the root of the `bitcoincorps` project directory you will now see a `ibd` ("initial block download") folder, and inside it a `one` folder. This folder represents all the code we wrote during the first lesson. With each now lesson, another such folder will show up. By the end you will have an `ibd` python package which does initial block download.
# 
# Check out the complete code from the first lesson: [`ibd/one/complete.py`](./ibd/one/complete.py). I changed a few thing, which I'll point out as we go.

# In[53]:


# Import the code from lesson 1
from ibd.one.complete import *


# Jupyter has an ["autoreload extensioin"](https://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html?highlight=reload#module-IPython.extensions.autoreload) that allows us to reimport `.py` files when we change them. Now that we have added a library of `.py` files this will be a helpful thing for us to do at the beginning of each lesson.

# In[54]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# ### Finding Our Place
# 
# Now we're back where we left off last time: we can send a hard-coded `version` message to a Bitcoin peer and make sense of the outermost attributes of the binary response we receive: "network magic", "command", "payload length", "payload checksum" and "payload" itself. But the information contained within the `payload` remains hidden from us.
# 
# ### Lesson 2 Objective
# 
# The goal of this lesson is to make sense of the payload you see after executing the cell below:

# In[55]:


import socket

PEER_IP = "35.198.151.21"
PEER_PORT = 8333

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

sock = socket.socket()
sock.connect((PEER_IP, PEER_PORT))

# initiate the "version handshake"
sock.send(VERSION)

# receive their "version" response
version_message = Packet.from_socket(sock)

print(version_message)


# ### Some Refactoring
# 
# Almost the same as last lesson except for:
# * I renamed `Message` to `Packet` because we're going to start defining things like `VersionMessage` and `VerackMessage` and so this seemed a little more clear.
# * `Packet` instances look like pretty tables when printed. This is because I added a `Network.__str__` method to [ibd/one/complete.py](./ibd/one/complete.py). `object.__str__` is the function Python calls when determining _how_ to print a given `object`. This `Packet.__str__` method simply runs a few of its values through this [tabulate](https://bitbucket.org/astanin/python-tabulate) program, which I added to our requirements.txt file.
# 
# ### The Payload
# 
# Our next task is to parse this payload. Besides the "/Satoshi:0.16.0/" -- clearly a user agent -- the rest of the payload isn't human readable.
# 
# But have no fear -- we will decode the message payload in the same manner as we decoded the overall message structure in our `Packet.from_socket` method from last class.
# 
# [This chart](https://en.bitcoin.it/wiki/Protocol_documentation#version) from the protocol documentation will act as our blueprint. A reprint:
# 
# ![image](./images/version-message.png)
# 
# ### Old Types
# 
# Here we encounter some "types" we are now familiar with from the first lesson -- `int32_t` / `uint64_t` / `int64_t` -- which are different types in a "low-level" language like C++, but are all equivalent to the `int` type in Python. Our previously implemented `bytes_to_int` can handle these just fine.
# 
# ### New Types
# 
# But we also encounter some new types: `net_addr`, `varstr`, and `bool`. 
# 
# Even worse, if we click on the [`varstr` link](https://en.bitcoin.it/wiki/Protocol_documentation#Variable_length_string) we see that it contains one additional type: `varint`. 
# 
# Worse still, the [`net_addr` link](https://en.bitcoin.it/wiki/Protocol_documentation#Network_address) contains `time`, `services` and `IPv6/4` fields nominally of types `uint32`, `uint64_t` and `char[16]` but in order for us to make sense of what they hell them mean each requires parsing: the `time` integer as a Unix timestamp, the `services` integer as a damn "bitfield" (whatever that is!), and `IPv6/4` IP address as a 16 digit bytestring where the first 12 digits are always `00 00 00 00 00 00 00 00 00 00 FF FF` and only the last 4 matter! 
# 
# Oh, and remember how I mentioned that Satoshi usually, but not always, encoded his integers in "little endian" byte order (least significant digits is on the left)? Well, the `port` attribute of `net_addr` is encoded "big endian", where the *most* significant digit is on the left. Yes, the exact opposite of everything else!!!
# 
# Hunker down for a looooooong lesson!

# # VersionMessage
# 
# Here's the outline of a `VersionMessage` class which will abstract the `version` [message type](https://en.bitcoin.it/wiki/Protocol_documentation#version):
# 
# * It has an `__init__` constructor method, which allows us to pass a different set of `version`, `services`, `timestamp`, `addr_recv`, `addr_from`, `nonce`, `user_agent`, `start_height`, and `relay` values to each new instance.
# * It will have a hard-coded ["class variable"](https://www.toptal.com/python/python-class-attributes-an-overly-thorough-guide) of `command = b"version"`. With this decision we are setting a convention: any instance of this class or the other 26 `Message` classes we still have to implement will have a `msg.command` attribute  to tell us what kind of message we're dealing with.
# * `VersionMessage.from_bytes` is also a convention that all 26 other `Message` classes will implement. Let's assume we are trying to handle an incoming `Packet` instance, which we will call `pkt`. We observe that `pkt.command` is `b"version`, so we're dealing with a version message and need to turn `pkt.payload` into an instance of the `VersionMessage` class defined in the cell above. The purpose of this `VersionMessage.from_bytes` classmethod is facilitate this: `msg = VersionMessage.from_bytes(pkt.payload)`. It's magic!
# * We will do some operations many times -- such as reading `n` bytes and interpreting them as a Python `int` -- so it makes sense to implement so-called "helper methods" to simplify our code, make it more testable and readable. `read_int`, `read_var_str`, `read_var_int` and `read_bool` are some such methods waiting to be implemented.

# In[56]:


def read_int(stream, n):
    raise NotImplementedError()
    
def read_var_int(stream):
    raise NotImplementedError()
    
def read_var_str(stream):
    raise NotImplementedError()
    
def read_bool(stream):
    raise NotImplementedError()
    
class VersionMessage:

    command = b"version"

    def __init__(self, version, services, timestamp, addr_recv, addr_from, 
                 nonce, user_agent, start_height, relay):
        self.version = version
        self.services = services
        self.timestamp = timestamp
        self.addr_recv = addr_recv
        self.addr_from = addr_from
        self.nonce = nonce
        self.user_agent = user_agent
        self.start_height = start_height
        self.relay = relay

    @classmethod
    def from_bytes(cls, payload):
        stream = BytesIO(payload)
        
        version = read_int(stream, 4)
        services = read_int(stream, 8)
        timestamp = read_int(stream, 8)
        addr_recv = stream.read(26)
        addr_from = stream.read(26)
        nonce = read_int(stream, 8)
        user_agent = read_var_str(stream)
        start_height = read_int(stream, 4)
        relay = read_bool(stream)

        return cls(version, services, timestamp, addr_recv, addr_from, 
                   nonce, user_agent, start_height, relay)


# # "Integer" Fields
# 
# In the last lesson we implemented `bytes_to_int(n)`. We'll start this lesson by implementing a small helper method `read_int(stream)` atop `bytes_to_int(n)` which first reads `n` from `stream` and then calls `bytes_to_int` with the bytes it read.
# 
# And we're going to create an argument `byte_order`, which defaults to `little`, because almost every integer our program deals with will be little-endian encoded. But IP ports -- and soon other -- are big-endian encoded so we must allow callers to override this `bytes_order="little"` default value if they have a big-endian endcoded integer on their hands.
# 
# ### Exercise #1: Implement `read_int(stream, n)`
# 
# Read `n` bytes and interpret it as an `int` with `byte_order` byte-order:

# In[57]:


# This cell is just some reminders of what kind of data we're dealing with
# Exercise is in the next cell ...

# stream will always be a BytesIO instance:
from io import BytesIO
stream = BytesIO(b'\x7f\x11\x01\x00\r\x04\x00\x00\x00\x00\x00\x00\xb4\x9dZ[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00b\x8f\xc9N~]\x00\xb2\x10/Satoshi:0.16.0/p%\x08\x00\x01')

# reminder: this is how you read 10 bytes from a stream / BytesIO instance:
stream.read(10) 


# In[59]:


def read_int(stream, n, byte_order='little'):
    # step 1: read the correct number of bytes from `stream` according to "field size" column above
    # step 2: interpret these bytes according to the "data type" column above
    ### replace `raise NotImplementedError()` with your code ###
    raise NotImplementedError()


# In[60]:


import ipytest, pytest
from io import BytesIO

data = [
    # number, number of bytes used to encode number, byte-order used to encode number
    [22, 10, 'little'],
    [1_000_000, 7, 'big'],
]

def test_read_int_0():
    for number, num_bytes, byte_order in data:
        bytes_ = number.to_bytes(num_bytes, byte_order)
        stream = BytesIO(bytes_)
        result = read_int(stream, num_bytes, byte_order)
        assert number == result
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_int*")


# ### To Help You Cheat
# 
# If you can't get the tests to pass, example solutions for all exercises can be found in [ibd/two/answers.py](./ibd/two/answers.py).

# ### Exercise #2: Read the version field contained within the payload of the version message (a mouthful, I know!)
# 
# hint: use `read_int` + protocol docs

# In[10]:


def read_version(stream):
    ### replace `raise NotImplementedError()` with your code ###
    raise NotImplementedError()


# In[11]:


import ipytest, pytest
import test_data

version_streams = test_data.make_version_streams()

def test_read_version_0():
    n = read_version(version_streams[0])
    assert n == 70015

def test_read_version_1():
    n = read_version(version_streams[1])
    assert n == 60001

def test_read_version_2():
    n = read_version(version_streams[2])
    assert n == 106
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_version*")


# 
# ### Exercise #3: Given a version message binary stream, tell me whether the node that sent it can send a `pong` message 
# 
# This exercise should give you a taste of the kind of information the version number encodes. [This table](https://bitcoin.org/en/developer-reference#protocol-versions) will show you the way!

# In[61]:


def can_send_pong(stream):
    ### replace `raise NotImplementedError()` with your code ###
    raise NotImplementedError()


# In[13]:


version_streams = test_data.make_version_streams()

def test_can_send_pong_0():
    result = can_send_pong(version_streams[0])
    assert result == True

def test_can_send_pong_1():
    result = can_send_pong(version_streams[1])
    assert result == True

def test_can_send_pong_2():
    result = can_send_pong(version_streams[2])
    assert result == False
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_can_send_pong*")


# # "Boolean" Fields
# 
# After the `int32_t` / `uint64_t` / `int64_t` integer-type fields, `bool` is the next simplest: it's a `1` or it's `0`. Actually, it's even simpler, huh? But we're going to resuse the code above so I'm introducing it second.
# 
# In fact, we could just use `read_int` and pass around `1`'s and `0`'s and our program would work just fine. After all, the statement `1 == True and 0 == False` evaluates to `True` in Python. But Python gives us a built-in `bool` class for dealing with true-or-false, 1-or-0 values because it gives our programs greater clarity and readability. Let's use it.
# 
# ### Exercise #4: implement `read_bool`

# In[17]:


def read_bool(stream):
    raise NotImplementedError()


# In[18]:


import test_data

def test_read_bool_0():
    stream = test_data.make_stream(test_data.true_bytes)
    result = read_bool(stream)
    assert type(result) == bool
    assert result is True
    
def test_read_bool_1():
    stream = test_data.make_stream(test_data.false_bytes)
    result = read_bool(stream)
    assert type(result) == bool
    assert result is False
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_bool_*")


# # "Timestamp" Fields
# 
# Network messages use ["Unix timestamps"](https://en.wikipedia.org/wiki/Unix_time) whenever they communicate some notion of "time". "Unix time" is just a running count of the number of seconds elapsed since the start of the year 1970 -- so it is represented as an integer.
# 
# Here's how we interpret a Unix timestamp in Python

# In[19]:


from datetime import datetime

def read_timestamp(stream):
    timestamp = read_int(stream, 8)
    return datetime.fromtimestamp(timestamp)


# # "Variable Length" fields
# 
# Next comes `var_str`, the type of the "User Agent", which is basically an advertisement of the Bitcoin software implementation that the node is using. You can see a listing of popular values [here](https://bitnodes.earn.com/nodes/).
# 
# ["Variable Length Strings"](https://en.bitcoin.it/wiki/Protocol_documentation#Variable_length_string) are used for string fields of unpredictible length. This technique strives to use only the space it needs. It does so by prepending a "variable length integer" in front of the string value being communicated, which tells the receiver how many bytes they should read in order to read the encoded string value. This is kind of similar to how the payload bytes are handled in our `Packet.from_socket` -- first we read `length` and then we read `length`-many bytes to get our raw payload. Same idea here, but now the length of the string isn't an integer, but a "variable length integer".
# 
# How does this `var_int` work?
# 
# The first byte of a `var_int` is a marker which says how many bytes come after it:
# * `0xFF`: 8 byte integer follows
# * `0xFE`: 4 byte integer follows
# * `0xFD`: 2 byte integer follows
# * < `0xFD`: 0 bytes follow. Interpret first byte as a 1 byte integer.
# 
# ### Exercise #5:  Implement `read_var_int`, since `read_var_str` will depend on it.
# 
# Since this is a somewhat complicated function, I've outlined it for you. Replace the `"FIXME"`s:

# In[21]:


def read_var_int(stream):
    i = read_int(stream, 1)
    if i == 0xff:
        return read_int(stream, 8)
    elif i == 0xfe:
        return "FIXME"
    elif "FIXME":
        return "FIXME"
    else:
        "FIXME"


# In[24]:


import ipytest, pytest
import test_data as td

enumerated = (
    (td.eight_byte_int, td.eight_byte_var_int),
    (td.four_byte_int, td.four_byte_var_int),
    (td.two_byte_int, td.two_byte_var_int),
    (td.one_byte_int, td.one_byte_var_int),
)

def test_read_var_int():
    for correct_int, var_int in enumerated:
        stream = td.make_stream(var_int)
        calculated_int = read_var_int(stream)
        assert correct_int == calculated_int

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_var_int*")


# Now that we have that out of the way:
# 
# ### Exercise #6: Implement `read_var_str`

# In[19]:


def read_var_str(stream):
    raise NotImplementedError()


# In[20]:


import ipytest, pytest
import test_data as td

enumerated = (
    (td.short_str, td.short_var_str),
    (td.long_str, td.long_var_str),
)

def test_read_var_str():
    for correct_byte_str, var_str in enumerated:
        stream = td.make_stream(var_str)
        calculated_byte_str = read_var_str(stream)
        assert correct_byte_str == calculated_byte_str

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_var_str*")


# # "Services" Field
# 
# [The version section of the protocol docs](https://en.bitcoin.it/wiki/Protocol_documentation#version) provides us with the following guide for interpreting the `services` field of the `version` payload:
# 
# ![image](images/services.png)
# 
# The type of this field is "bitfield". [Check out the wikipedia entry](https://en.wikipedia.org/wiki/Bit_field) for a more detailed explanation that I can provide.
# 
# A bitfield is an integer. Every bit of the base-2 representation (e.g. "101" is base-2 representation of 5) holds some pre-defined meaning. This particular bitfield is 8 bytes / 64 bits (remember, a byte is just a collection of 8 bits so 8 bytes is 8*8=64 bits).
# 
# From the table above we can see that the least significant digit in the binary representation (decimal value `2^0=1`) represents `NODE_NETWORK`, or whether this peer "can be asked for full blocks or just headers".
# 
# The second least-significant digit (decimal value `2^1=2`): `NODE_GETUTXO`
# 
# The third least-significant digit (decimal value `2^2=4`): `NODE_BLOOM`
# 
# The fourth least-significant digit (decimal value `2^3=8`): `NODE_WITNESS`
# 
# The eleventh least-significant digit (decimal value `2^10=1024`): `NODE_NETWORK_LIMITED`
# 
# The rest of the bits (decimal values `2*n` where n in {4, 5, 6, 7, 8, 9, 11, 12, ..., 63} have no meaning, yet.
# 
# So, in order to interpret this field we need to look up the nth bit in the table above and see if it means anything.
# 
# So, our Python code could produce a dictionary like this for every node we connect to. This would allow us to look up what services that node offers _by name_ (which is why it's called a dictionary!):
# 
# ```
# {
#     'NODE_NETWORK': True,
#     'NODE_GETUTXO': False,
#     'NODE_BLOOM': True,
#     'NODE_WITNESS': False,
#     'NODE_NETWORK_LIMITED': True,
# }
# ```
# 
# Furthermore, we could write a function that produces this lookup table for us given an integer bitfield and a magical `check_bit(n)` function:
# 
# ```
# def read_services(stream):
#     n = read_int(stream, 4)
#     return {
#         'NODE_NETWORK': check_bit(services_int, 0),           # 1    = 2**0
#         'NODE_GETUTXO': check_bit(services_int, 1),           # 2    = 2**1
#         'NODE_BLOOM': check_bit(services_int, 2),             # 4    = 2**2
#         'NODE_WITNESS': check_bit(services_int, 3),           # 8    = 2**3
#         'NODE_NETWORK_LIMITED': check_bit(services_int, 10),  # 1024 = 2**10
#     }
# ```
# 
# For now, I'm just going to give you a definition of the magical `check_bit` function:

# In[25]:


def check_bit(number, index):
    """See if the bit at `index` in binary representation of `number` is on"""
    mask = 1 << index
    return bool(number & mask)


# ### Exercise #7: Fill out the remainder of the `services_int_to_dict` and `read_services` functions:
# 
# Replace each occurrence of `FIXME` with correct numbers

# In[22]:


def services_int_to_dict(services_int):
    return {
        'NODE_NETWORK': check_bit(services_int, "FIXME"),
        'NODE_GETUTXO': check_bit(services_int, "FIXME"),
        'NODE_BLOOM': check_bit(services_int, "FIXME"),
        'NODE_WITNESS': check_bit(services_int, "FIXME"),
        'NODE_NETWORK_LIMITED': check_bit(services_int, "FIXME"),
    }

def read_services(stream):
    services_int = read_int(stream, "FIXME")
    return "FIXME"


# In[27]:


import ipytest, pytest
import test_data as td

def test_read_services():
    services = 1 + 2 + 4 + 1024
    answer = {
        'NODE_NETWORK': True,
        'NODE_GETUTXO': True,
        'NODE_BLOOM': True,
        'NODE_WITNESS': False,
        'NODE_NETWORK_LIMITED': True,
    }
    stream = BytesIO(int_to_bytes(services, 8))
    assert read_services(stream) == answer

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_services*")


# To give you a better idea what's going on here, check out these `read_services` outputs for some possible inputs:

# In[28]:


from pprint import pprint

bitfields = [
    1,
    8,
    1 + 8,
    1024,
    8 + 1024,
    1 + 2 + 4 + 8 + 1024,
    2**5 + 2**9 + 2**25,
]

for bitfield in bitfields:
    pprint(f"(n={bitfield})")
    stream = BytesIO(int_to_bytes(bitfield, 4))
    pprint(read_services(stream))
    print()


# ### Exercise #8: Complete these function definitions to hammer home you understanding of this strange `services` "bitfield"

# In[29]:


def offers_node_network_service(services_bitfield):
    # given integer services_bitfield, return whether the NODE_NETWORK bit is on
    raise NotImplementedError()

def offers_node_bloom_and_node_witness_services(services_bitfield):
    # given integer services_bitfield, return whether the 
    # NODE_BLOOM and NODE_WITNESS bits are on
    raise NotImplementedError()


# In[30]:


import ipytest, pytest

def test_services_0():
    assert offers_node_network_service(1) is True
    assert offers_node_network_service(1 + 8) is True
    assert offers_node_network_service(4) is False
    

def test_services_1():
    assert offers_node_bloom_and_node_witness_services(1) is False
    assert offers_node_bloom_and_node_witness_services(1 + 8) is False
    assert offers_node_bloom_and_node_witness_services(4 + 8) is True
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_services*")


# # "Network Address" Type
# 
# [`net_addr`](https://en.bitcoin.it/wiki/Protocol_documentation#Network_address) is the most complicated new type we encounter this lesson, so we'll handle it last. Plus, it builds on the `timestamp` and `services` types we learned to read above.
# 
# ![image](images/network-address.png)
# 
# Network addresses require we interpret 4 new kinds of data:
# 
# 1. `time`: Unix timestamp. Already done.
# 2. `services`: integer bitfield. Already done.
# 3. `IP address`: complicated ...
# 4. `port`: big-endian encoded `int`
# 
# Here's a Python class abstracting this "Network Address" type. 
# 
# * `read_ip` and `read_port` functions await implementation
# * `net_addr` doesn't contain a `time` when it's inside a `version` message. Yup, that's confusing to me too. The `if-else` statement in `Address.from_stream` is my best attempt at translating what the documentation describes. Once again, we'll employ an argument with a default value `version_msg=False` to allow whoever calls `Address.from_stream` to tell it whether it's inside a version message or not. We'll see if this works!

# In[47]:


def read_ip(stream):
    raise NotImplementedError()

def read_port(stream):
    raise NotImplementedError()
    
class Address:

    def __init__(self, services, ip, port, time):
        self.services = services
        self.ip = ip
        self.port = port
        self.time = time

    @classmethod
    def from_stream(cls, stream, version_msg=False):
        if version_msg:
            time = None
        else:
            time = read_timestamp(stream)
        services = read_services(stream)
        ip = read_ip(stream)
        port = read_port(stream)
        return cls(services, ip, port, time)
    
    def __repr__(self):
        return f"<Address {self.ip}:{self.port}>"


# ### Exercise #9: Implement `read_ip`
# 
# hint: read n bytes where n is in the chart above, and return `ip_address(those_bytes)`

# In[48]:


from ipaddress import ip_address

def read_ip(stream):
    raise NotImplementedError()


# In[49]:


import ipytest, pytest

def test_read_ip_0():
    ipv4 = '10.10.10.10'
    ipv4_mapped = b'\x00'*10 + b'\xff'*2 + ip_address(ipv4).packed
    stream = BytesIO(ipv4_mapped)    
    assert read_ip(stream).ipv4_mapped.compressed == ipv4
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_ip*")


# ## "Network Address > Port" Field
# 
# This is just 2 byte integer -- but it's encoded with the opposite byte order of what we usually read using `read_bytes`. But have no fear, `read_bytes` takes an optional `byte_order` parameter which defaults to `"little"` -- since we're usually reading little-endian encoded messages. But if we set it to `"big"`, then `read_int` will successfully read the "big endian" / "network byte order" port integer.
# 
# In order to have clean, testable code we will define another helper method: `read_port`
# 
# ### Exercise #10: Implement `read_port`

# In[50]:


def read_port(stream):
    raise NotImplementedError()


# In[51]:


import ipytest, pytest
from io import BytesIO

ports = [8333, 55555]

def test_read_port_0():
    for port in ports:
        bytes_ = port.to_bytes(2, 'big')
        stream = BytesIO(bytes_)
        result = read_port(stream)
        assert port == result
    
ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_read_port*")


# # Parsing a complete Version response
# 
# Let's put together all the little helper function and helper classes we've so dilligently written and parse the payload of the `version` message we downloaded at the beginning of this lesson.

# In[1]:


import socket
from ibd.two.complete import Packet, VersionMessage # get the final version ...

PEER_IP = "35.198.151.21"

PEER_PORT = 8333

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

sock = socket.socket()
sock.connect((PEER_IP, PEER_PORT))

# initiate the "version handshake"
sock.send(VERSION)

# receive their "version" response
pkt = Packet.from_socket(sock)

msg = VersionMessage.from_bytes(pkt.payload)
print(msg)


# In[1]:


print(1_000_000)


# Boom! This is basically the same code we finished the last lesson with, but our magical `version_report` function and all the functions it calls are able to decipher what this cryptic message _means_!
# 
# Some work is left. What the heck do the `net_addr` fields mean? What kind of `versions` are most people running. Are most people `relay`ing, or not?
# 
# In the next lesson we'll connect with every Bitcoin full node we can find and try to answer some of these questions!
