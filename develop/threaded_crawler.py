import socket
import threading
from ipaddress import ip_address

from ibd import Packet, VerackMessage, VersionMessage

# FIXME
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

connected_to = []
threads = []


def connect(address):
    ipv4 = ip_address(address[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    sock = socket.socket(param)
    # sock.settimeout(5)
    sock.connect(address)
    sock.send(VERSION)
    connected_to.append(address)
    try:
        main_loop(sock, address)
    finally:
        connected_to.remove(address)  # FIXME: this won't happen if there's an exception
        sock.close()


def threaded_connect(address):
    thread = threading.Thread(target=connect, args=(address,))
    threads.append(thread)
    thread.start()


def main_loop(sock, a):
    while True:
        try:
            pkt = Packet.from_socket(sock)
            print(f"received {pkt.command} from {a}")
            if pkt.command == b"version":
                version_message = VersionMessage.from_bytes(pkt.payload)
                verack_packet = Packet(command=b"verack", payload=b"")
                sock.send(verack_packet.to_bytes())
            elif pkt.command == b"verack":
                verack_message = VerackMessage.from_bytes(pkt.payload)
                # getaddr = Packet(command=b"getaddr", payload=b"")
                # sock.send(getaddr.to_bytes())
        except RuntimeError as e:
            print("Runtime Error:", e)
            continue
        except Exception as e:
            print("Unhandled exception:", e)
            break


def main():
    address = ("46.226.18.135", 8333)
    threaded_connect(address)


if __name__ == "__main__":
    main()
