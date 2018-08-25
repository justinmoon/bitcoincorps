import socket
import time

from ibd.three.complete import *  # get the final version ...


def handshake(address, log=True):
    # Arguments for our outgoing VersionMessage
    services = 1
    my_ip = "7.7.7.7"
    peer_ip = address[0]
    port = address[1]
    now = int(time.time())
    my_address = Address(services, my_ip, port, time=None)
    peer_address = Address(services, peer_ip, port, time=None)

    # Create out outgoing VersionMessage and Packet instances
    version_message = VersionMessage(
        version=70015,
        services=services,
        time=now,
        addr_from=my_address,
        addr_recv=peer_address,
        nonce=73948692739875,
        user_agent=b"bitcoin-corps",
        start_height=0,
        relay=1,
    )
    version_packet = Packet(
        command=version_message.command, payload=version_message.to_bytes()
    )
    serialized_packet = version_packet.to_bytes()

    # Create the socket
    sock = socket.socket()

    # Initiate TCP connection
    sock.connect(address)

    # Initiate the Bitcoin version handshake
    sock.send(serialized_packet)

    # Receive their "version" response
    pkt = Packet.from_socket(sock)
    peer_version_message = VersionMessage.from_bytes(pkt.payload)
    if log:
        print(peer_version_message)

    # Receive their "verack" response
    pkt = Packet.from_socket(sock)
    peer_verack_message = VerackMessage.from_bytes(pkt.payload)
    if log:
        print(peer_verack_message)

    # Send out "verack" response
    verack_message = VerackMessage()
    verack_packet = Packet(verack_message.command, payload=verack_message.to_bytes())
    sock.send(verack_packet.to_bytes())

    return sock
