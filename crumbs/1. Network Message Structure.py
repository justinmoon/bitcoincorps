
# coding: utf-8

# # Where to Start?

# When we describe Bitcoin to our friends and enemies, we often struggle to decide which aspect to describe first. Bitcoin has many facets and a perfect explanation of any single facet usually tails to do justice to the whole. Here's a few facets of Bitcoin:
# * Hard money, deflationary monetary policy
# * Anarchic, ungovernable FOSS project
# * Programmable money
# * Payment system
# * Censorship-resistant P2P file sharing network
# * A ledger
# 
# Describing Bitcoin as software is similarly difficult. Here's a few facets of Bitcoin in this context:
# * An internet protocol atop TCP/IP
# * Smart contracting system
# * A "Blockchain"
# * A set of transaction abstractions (TxIn, TxOut, script hashes)
# 
# This course will begin with the network protocol aspect. I choose this for a few reasons: 
# * Network programming is very fun.
# * We all use the internet, but don't really understand how it works. Here's our chance to dig in and understand a little more deeply.
# * We can be "hands on" from the very first. We will connect directly to [full nodes](https://bitnodes.earn.com/nodes/) and learn to speak their language.
# * As we go deeper I will introduce whatever concepts are needed to understand what our peers are telling us. In a sense, this is a very empirical approach!

# # Connecting to the Bitcoin Network
# 
# OK! Let's connect to the Bitcoin Network.
# 
# Since the Bitcoin Network is peer-to-peer, we must find some specific peer to connect to.
# 
# [This site](https://bitnodes.earn.com/nodes/) has a nice listing of visible nodes in the Bitcoin network. Choose one. Look at the "address" column. You should see something like "35.187.200.6:8333". This is the "address" of the node you've selected. This address is composed of two values: an Internet Protocol (IP) address (e.g. 35.187.200.6), and a port (e.g. 8333) separated by a colon.
# 
# Paste in the IP and port of the node you selected in the cell below.

# In[7]:


# FILL THESE IN!
PEER_IP = ""
PEER_PORT = 0


# Here's how to open a raw socket connection to an IP:Port pair.

# In[8]:


import socket

sock = socket.socket()
sock.connect((PEER_IP, PEER_PORT))

response = sock.recv(1024)

print("response: ", response)


# OK. We created a socket, which like a tunnel across the internet that behaves like a file. You can write data into a socket using `sock.send(message_bytes)` and read from a socket using `sock.recv(number_of_bytes_to_read)`. Similar to a file.
# 
# But nothing happened. Actually, the socket is still attempting to receive bytes over the TCP connection. The code is blocked on the line `response = sock.recv(1024)`. This will wait forever until the Bitcoin node at the other end of our socket connection sends us a response.
# 
# You may have noticed that to the left of every Jupyter cell is the text `In [ ]:` if the cell hasn't been executed yet, and somthing like `In [7]:` if the cell was the 7th cell executed. But the cell above says `In [*]:`. This means that it's still executing. The code is stuck. Press `escape ii` or hit the ■ button in the menu above to tell Jupyter to kill the process in the cell above.
# 
# The reason the code is stuck is because we didn't properly introduce ourselves to our peer. With Bitcoin, we must perform a [Version Handshake](https://en.bitcoin.it/wiki/Version_Handshake) in order to begin exchanging messages.
# 
# So let's try again. I'm going to give you a `VERSION` bytestring without telling you how I came up with it. Before calling `sock.recv(1024)` we will first call `sock.send(VERSION)` because the Bitcoin Version Handshake demands that the node which initiates the connection send the first `version` message.

# In[9]:


import socket

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

sock = socket.socket()
sock.connect((PEER_IP, PEER_PORT))

# initiate the "version handshake"
sock.send(VERSION)

# receive their "version" response
response = sock.recv(1024)

print(response)


# The code no longer gets stuck at `response = sock.recv(1024)` because the peer answered our `version` message with their own `version` message. We're learning to say "hello" in the language of the Bitcoin network protocol!
# 
# This table in the [protocol documentation](https://en.bitcoin.it/wiki/Protocol_documentation#version) tells us what information the `version` message contains and how to decipher it. But before we can read the version message specifically (as opposed to the other 26 types), we need to learn to read a Bitcoin protocol message generally. This ["message structure"](https://en.bitcoin.it/wiki/Protocol_documentation#Message_structure) table tells us how.
# 
# The "description" and "comments" columns tell us what each row in the table means. The "field size" column tell us the number of bytes each field takes up, and the "data type" column tells us how we should interpret these bytes -- e.g. whether they a number, a string, a list etc.
# 
# Here's the value I received when I ran the previous cell:
# 
# ```
# b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00f\x00\x00\x00\xc6\xa7\xa2(\x7f\x11\x01\x00\r\x04\x00\x00\x00\x00\x00\x00&\xffT[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00$\xfa\t\n\xc5y\xf7\t\x10/Satoshi:0.16.0/\xae"\x08\x00\x01'
# ```
# 
# Here's how to read the 5 fields in the ["message structure"](https://en.bitcoin.it/wiki/Protocol_documentation#Message_structure) table:

# In[10]:


version_bytes = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00f\x00\x00\x00\xc6\xa7\xa2(\x7f\x11\x01\x00\r\x04\x00\x00\x00\x00\x00\x00&\xffT[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00$\xfa\t\n\xc5y\xf7\t\x10/Satoshi:0.16.0/\xae"\x08\x00\x01'

print('4 "magic" bytes: ', version_bytes[:4])
print('12 "command" bytes: ', version_bytes[4:4+12])
payload_length_bytes = version_bytes[4+12:4+12+4]
# here I actually interpret these bytes as an integer
# more on this later!
payload_length = int.from_bytes(payload_length_bytes, 'little')
print('4 "length" bytes', payload_length_bytes)
print('4 "checksum" bytes', version_bytes[4+12+4:4+12+4+4])
print(payload_length, ' "payload" bytes', version_bytes[4+12+4+4:4+12+4+4+payload_length])


# It's ugly as sin, but by simply [slicing](https://stackoverflow.com/questions/509211/understanding-pythons-slice-notation) the `version_bytes` we can extract:
# 
# * `version`: first 4 bytes
# * `command`: next 12 bytes
# * `length`: next 4 bytes
# * `checksum`: next 4 bytes
# * `payload`: next `length` bytes
# 
# While indexing is conceptualy simple, it's confusing and fragile.
# 
# Can't we agree that a better way would be some function like `read(version_bytes, n)` which would just read the next n bytes? Kind of like how we read from the socket earlier: `sock.recv(1024)`. This way we wouldn't need to keep track of how many bytes we've already read (e.g. `4+12+4+4`).
# 
# Well I have good news. The Python Standard Library contains a [io.BytesIO](https://docs.python.org/3/library/io.html#io.BytesIO) class that does exactly this. 
# 
# The only problem is that we need to call `instance.read` to read from an `io.BytesIO` instance and `instance.recv` to read from a `socket.socket` instance. Since we want all our code to work with sockets, we can create a stupid little `FakeSocket` helper class which can keep our code socket-compatibile while we develop it.

# In[20]:


from io import BytesIO

class FakeSocket:
    
    def __init__(self, bytes_):
        self.stream = BytesIO(bytes_)
        
    def recv(self, n):
        return self.stream.read(n)
    
    
def create_version_socket(skip_bytes=0):
    version_bytes = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00f\x00\x00\x00\xc6\xa7\xa2(\x7f\x11\x01\x00\r\x04\x00\x00\x00\x00\x00\x00&\xffT[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00$\xfa\t\n\xc5y\xf7\t\x10/Satoshi:0.16.0/\xae"\x08\x00\x01'[skip_bytes:]
    return FakeSocket(version_bytes)


# In[12]:


sock = create_version_socket()

print('4 "magic" bytes: ', sock.recv(4))
print('12 "command" bytes: ', sock.recv(12))
payload_length_bytes = sock.recv(4)
# here I actually interpret these bytes as an integer
# more on this later!
payload_length = int.from_bytes(payload_length_bytes, 'little')
print('4 "length" bytes', payload_length_bytes)
print('4 "checksum" bytes', sock.recv(4))
print(payload_length, ' "payload" bytes', sock.recv(payload_length))


# `sock.recv(payload_length)` is a lot easier to read than `version_bytes[4+12+4+4:4+12+4+4+payload_length]`, wouldn't you say?
# 
# This also fixes a huge bug that exists the line of code above: `response = sock.recv(1024)`.
# 
# This statement reads a fixed number of bytes no matter what. 1024 bytes will probably never be enough to read a `block` message, but it's often too much for a `version` message. For example, if you try running the first socket example with enough peers you will eventually see something like this: 
# 
# ```
# b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00f\x00\x00\x00f\x9a\xe5\x06\x7f\x11\x01\x00\r\x04\x00\x00\x00\x00\x00\x00\xb9kV[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x92\xed.\xd6\xba\x90\xa8\t\x10/Satoshi:0.16.0/d#\x08\x00\x01\xf9\xbe\xb4\xd9verack\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00]\xf6\xe0\xe2'
# ```
# 
# If you look closely you may notice that the magic network string `\xf9\xbe\xb4\xd9` (explained in next cells) appears twice. `version` follows the first occurrence, and `verack` follows the second. This is not one message! It's two!
# 
# By always reading exactly the number of bytes we need -- as in the cell above -- we can avoid this problem.

# # Read Network Magic

# The protocol documentation from earlier lists `0xD9B4BEF9` as the `magic` value for Bitcoin's "main" network. This integer (represented in hexidecimal / base 16) identifies TCP packets as Bitcoin network packets. To know whether your program is working with a Bitcoin protocol message it is sufficient to check whether the first 4 bytes of the message are equivalent to the integer `0xD9B4BEF9`.
# 
# Furthermore, the protocol docs state that this value is "sent over the network" as `F9 BE B4 D9`. Notice how similar this is to the `\xf9\xbe\xb4\xd9` value printed above. If you take `\xf9\xbe\xb4\xd9`, replace `\x`'s with spaces and then uppercase it, you have `F9 BE B4 D9`.
# 
# If you take `\xf9\xbe\xb4\xd9'`, reverse the groups of bytes (`\xd9\xb4\xbe\xf9`), strip the `\x` byte prefixes (`d9b4bef9`), uppercase it (`D9B4BEF9`), and prepend with `0x` prefix to indiciate it's a hexidecimal number (`0xD9B4BEF9`) we arrive at the Bitcoin's magic integer.
# 
# I expect you're extremely confused right now. I, too, was extremely confused when I first encountered this. But I hope you can also see that there's some pattern to the madness ...

# In[13]:


# hexidecimal integers copied from protocol documentation
NETWORK_MAGIC = 0xD9B4BEF9
TESTNET_NETWORK_MAGIC = 0x0709110B

# notice this looks like any old integer even though we declared it
# using a hexidecimal notation. Under the hood Python stores every integer
# as base 2 and doesn't care what base integers were initialized in.
print("NETWORK_MAGIC:", NETWORK_MAGIC)
print("TESTNET_NETWORK_MAGIC:", TESTNET_NETWORK_MAGIC)


# In[14]:


def bytes_to_int(b):
    return int.from_bytes(b, 'little')

def read_magic(sock):
    magic_bytes = sock.recv(4)
    magic = bytes_to_int(magic_bytes)
    return magic
    
def is_mainnet_msg(sock):
    magic = read_magic(sock)
    return magic == NETWORK_MAGIC

def is_testnet_msg(sock):
    magic = read_magic(sock)
    return magic == TESTNET_NETWORK_MAGIC


print("Mainnet version message?", is_mainnet_msg(create_version_socket()))
print("Testnet version message?", is_testnet_msg(create_version_socket()))


# The above code is pretty straightforward, with two exceptions:
# 
# * hexidecimal numbers: `0xD9B4BEF9` and `0x0709110B`
# * bytes -> int conversion: `int.from_bytes(b, 'little')`
# 
# 

# ### Hexidecimal 
# 
# In Python you prefix a number with `0x` to tell the interpreter to interpret it as hexidecimal (base 16), `0o` for octal (base 8), `0b` for binary (base 2). But once you've created the integer, Python forgets what base you used to create it. `17`, `0b10001`, `0o21`, and `0x11` are all equivalent. 
# 
# There are built-in `bin`, `oct`, and `hex` function that take an integer and give you a string representation of the integer in a different base. But they don't actually change the integer because under the hood all integers are stored as base 2 in Python.

# In[1]:


# FIXME: Exercises

n = 17

print(n, "is:")
print(bin(n),"in binary.")
print(oct(n),"in octal.")
print(hex(n),"in hexadecimal.")

# These just print out the string representation of n in a different base
print("type of bin()/oct()/hex()?", type(bin(n)), type(oct(n)), type(hex(n)))

print("17 == 0b10001 == 0o21 == 0x11?", 17 == 0b10001 == 0o21 == 0x11)


# In[3]:


print(type(hex(n)))
print(hex(n))


# ### bytes -> int
# 
# Time to talk "endianness". Yes, "endianness".
# 
# The Internet Protocol is just a system to send packets of bytes to an address. But there are two ways to send the bytes:
# 
# > In big-endian format, whenever addressing memory or sending/storing words bytewise, the most significant byte—the byte containing the most significant bit—is stored first (has the lowest address) or sent first, then the following bytes are stored or sent in decreasing significance order, with the least significant byte—the one containing the least significant bit—stored last (having the highest address) or sent last.
# 
# > Little-endian format reverses this order: the sequence addresses/sends/stores the least significant byte first (lowest address) and the most significant byte last (highest address). Most computer systems prefer a single format for all its data; using the system's native format is automatic. But when reading memory or receiving transmitted data from a different computer system, it is often required to process and translate data between the preferred native endianness format to the opposite format.
# 
# (from [Wikipedia](https://en.wikipedia.org/wiki/Endianness))
# 
# If we look once again at the magic values chart from the protocol documentation:
# 
# ![image](./images/magic-values.png)
# 
# You see that the most significant byte for the main network magic is `D9`. This is just how we write numbers: the biggest digit is to the left.
# 
# But it's sent over the wire as `F9 BE B4 D9` -- now the biggest / most-significant byte is to the right and the smallest / least-significant byte (`F9`) is to the left. This is because it's been encoded "little-endian". Now our `bytes_to_int` definition should make a little more sense:
# 
# ```
# def bytes_to_int(b):
#     return int.from_bytes(b, 'little')
# ```
# 
# We're just taking a bytestring and converting to an integer, and python demands we specify the byteorder ('little'). [Here's the relevant section of the Python documentation](https://docs.python.org/3/library/stdtypes.html#int.from_bytes).
# 
# Try creating another cell in this Jupyter Notebook (Insert > Cell Below, or type "escape" then "b") and running `int.from_bytes('\x00')`. You will get an error because Python demands you specify the byteorder -- whether the bytes are little- or big-endian encoded.
# 
# 
# Another expression you might try to evaluate is `int.from_bytes(b"\x00\x01", "little") == int.from_bytes(b"\x01\x00", "big")`. The beauty of Jupyter Notebook is that you can always create a new cell and test to see whether I'm lying!
# 
# 
# If you're confused, don't despair. We'll be doing a TON of little-endian decoding and encoding. We'll even do some big-endian encoding because Satoshi didn't make up his mind and stick to a consistent byteorder. In particular, public keys, IP and port numbers are encoded big-endian.

# In[18]:


int.from_bytes(b"\x00\x01", "little") == int.from_bytes(b"\x01\x00", "big")


# TODO: add some exercises (e.g. write the number 500 in big endian)

# # Read `command`
# 
# Let's try to parse the 12 byte "command" section of the message
# 
# ![image](./images/message-structure.png)

# In[21]:


# FIXME: demonstrate how to read without stripping empty bytes

sock = create_version_socket(skip_bytes=4)
print(sock.recv(12))


# In[22]:


# FIXME: should be an exercise

def read_command(sock):
    raw = sock.recv(12)
    # remove empty bytes
    command = raw.replace(b"\x00", b"")
    return command
    
def is_version_msg(sock):
    command = read_command(sock)
    return b"version" == command
    
def is_verack_msg(sock):
    command = read_command(sock)
    return b"verack" == command

# Throw away the first 4 bytes (the magic)
sock = create_version_socket(skip_bytes=4)
command = read_command(sock)
print("Command: ", command)

sock = create_version_socket(skip_bytes=4)
print("Is it a 'version' message?", is_version_msg(sock))

sock = create_version_socket(skip_bytes=4)
print("Is it a 'verack' message?", is_verack_msg(sock))


# ### Message Payload
# 
# Let's try to parse the 3 payload-related portions of the message: "length", "checksum", and "payload"
# 
# ![image](./images/message-structure.png)
# 
# The whole goal of these three attributes is to read the payload -- which could be a newly mined block, or a transaction, or the address of a newly connected bitcoin full node -- and verify that the payload wasn't corrupted at all in transmission over the internet.
# 
# Payloads vary in length. A [`verack` message](https://en.bitcoin.it/wiki/Protocol_documentation#verack) has empty payload. A [`block` message](https://en.bitcoin.it/wiki/Protocol_documentation#block) payload may contain thousands of transactions, each with tens of inputs and outputs.
# 
# To deal with the varying lengths of message payloads, the Bitcoin protocol messages always include a `length` parameter which tells us exactly how many bytes to read. This helps us avoid only reading part of the payload and stopping, or overshooting and reading into the next message (like the example above where I read two messages by accident).
# 
# And once we read the payload, how can we be sure that what we receive is the same as what our peer node sent us?
# 
# Well, TCP ensures against packet loss using checksums and the Bitcoin network protocol is just a thin layer on top of TCP. [But apparently its checksumming mechanism (which I don't understand) may be less effective than `sha256`](https://bitcoin.stackexchange.com/questions/22882/what-is-the-function-of-the-payload-checksum-field-in-the-bitcoin-protocol). In any case, Satoshi implemented a further ["checksum"](https://en.wikipedia.org/wiki/Checksum) to guarantee data integrity.
# 
# Checksums are a simple idea: You take the message and run it through a [hashing algorithm](https://blog.jscrambler.com/hashing-algorithms/) -- in this case you run it through `sha256` twice -- and take just a few bytes of the result -- in this case the first 4. Given an input `x`, a hashing algorithm `h` will always produce the same output `h(x)`. Since the output is the same, the first four digits of the output will always be the same. And since the key property of hashing functions is going from `h(x) -> x` requires brute forcing, you'd need to try about 256^4 ≈ 500,000,000 values (a byte contains 256 possible values and there are 4 bytes) on average to fake any given payload without modifying the checksum. So I guess Satoshi thought that would help!

# FIXME: some better checksum explainer (video)

# In[36]:


from hashlib import sha256

def read_length(sock):
    raw = sock.recv(4)
    length = bytes_to_int(raw)
    return length

def read_checksum(sock):
    # FIXME: protocol documentation says this should be an integer ...
    raw = sock.recv(4)
    # FIXME: turn into integer
    return raw

def calculate_checksum(payload_bytes):
    """First 4 bytes of sha256(sha256(payload))"""
    first_round = sha256(payload_bytes).digest()
    second_round = sha256(first_round).digest()
    first_four_bytes = second_round[:4]
    # FIXME: turn into integer
    return first_four_bytes

def read_payload(sock, length):
    payload = sock.recv(length)
    return payload

# skip the "magic" and "command" bytes
sock = create_version_socket(skip_bytes=4+12)

length = read_length(sock)
checksum = read_checksum(sock)
payload = read_payload(sock, length)

print("Length: ", length)

print("Checksum: ", checksum)

print("Payload: ", payload)

print("checksum == calculate_checksum(payload)?: ", 
      checksum == calculate_checksum(payload))


# And there we go! We know how to parse all from a Bitcoin protocol message!
# 
# Lastly, let's create a class that abstracts a Bitcoin protocol message.

# In[44]:


class Message:
    
    def __init__(self, command, payload):
        self.command = command
        self.payload = payload

    @classmethod
    def read_from_socket(cls, sock):
        magic = read_magic(sock)
        if magic != NETWORK_MAGIC:
            raise ValueError('Network magic is wrong')

        command = read_command(sock)
        payload_length = read_length(sock)
        checksum = read_checksum(sock)
        print("checksum", checksum)
        payload = read_payload(sock, payload_length)
        
        calculated_checksum = calculate_checksum(payload)
        if calculated_checksum != checksum:
            raise RuntimeError("Checksums don't match")

        return cls(command, payload)

    def __repr__(self):
        return f"<Message command={self.command} payload={self.payload}>"


# In[45]:


import socket

PEER_IP = "52.33.162.224"

PEER_PORT = 8333

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

sock = socket.socket()
sock.connect((PEER_IP, PEER_PORT))

# initiate the "version handshake"
sock.send(VERSION)

# receive their "version" response
msg = Message.read_from_socket(sock)

print(msg)


# There you go. You now know how to read a Bitcoin message directly from a raw socket, verify that it is structured correctly, and interpret it as an instance of a Python `Message` class.
# 
# You are almost ready to do the [Version Handshake](https://en.bitcoin.it/wiki/Version_Handshake) unassisted. We just need to learn how to read and create `version` and `verack` payloads. We'll cover this in the next lesson!
