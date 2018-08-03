# TODO timer generator https://youtu.be/D1twn9kLmYg?t=19m46s
# TODO: print which thread all of these are in.
# people won't understand / believe how this is happening in a completely different way
import asyncio
import concurrent.futures
import os
import queue
import random
import socket
import sys
import threading
import time
from functools import wraps

import matplotlib.pyplot as plt
import numpy as np
import requests

from ibd.two.complete import (Packet, VersionMessage, bytes_to_int,
                              calculate_checksum)

# FIXME: overwriting import
NETWORK_MAGIC = b"\xf9\xbe\xb4\xd9"

# magic "version" bytestring
VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'


def get_nodes():
    url = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    response = requests.get(url)
    return response.json()["nodes"]


def nodes_to_addrs(nodes):
    raw_addrs = nodes.keys()
    addrs = []
    for raw_addr in raw_addrs:
        ip, port = raw_addr.rsplit(":", 1)
        addr = (ip, int(port))
        addrs.append(addr)
    return addrs


def get_addrs():
    nodes = get_nodes()
    return nodes_to_addrs(nodes)


def timed(func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    stop = time.time()
    return (result, start, stop)


def connect_synchronous(addr):
    try:
        sock = socket.socket()
        sock.settimeout(1)
        sock.connect(addr)
        sock.send(VERSION)
        pkt = Packet.from_socket(sock)
        msg = VersionMessage.from_bytes(pkt.payload)
        sock.close()
        return msg
    except:
        return None


def connect_many_synchronous(addrs):
    for addr in addrs:
        connect(addr)


def connect_many_threaded_list(addrs):
    threads = []

    # spawn 10 threads and start them
    # append the threads to `threads` list so that we can wait for them to finish
    # one problem -- can't get the results!
    for addr in addrs[:10]:
        thread = threading.Thread(
            target=lambda addr: print(connect_synchronous(addr)), args=(addr,)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def connect_many_threaded_list_with_return_vals(addrs):
    # https://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread-in-python
    # second answer here

    results = []
    threads = []

    def connect_synchronous_and_record_return_value(addr, results):
        # get the version response from peer
        # append it to a python list that lives in the main thread
        result = connect_synchronous(addr)
        results.append(result)

    # spawn 10 threads and start them
    # append the threads to `threads` list so that we can wait for them to finish
    for addr in addrs[:10]:
        thread = threading.Thread(
            target=connect_synchronous_and_record_return_value, args=(addr, results)
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    for result in results:
        print(result)


def connect_many_threadpool(addrs):
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(timed, connect_synchronous, addr) for addr in addrs]
        result = concurrent.futures.wait(futures)
        # could also use add_done_callback
        done, not_done = result
        return done


def threadpool_result_to_start_stop_tups(result):
    results = [f.result() for f in result if f.result() is not None]
    start_stop = [(start, stop) for (msg, start, stop) in results]
    start_stop = sorted(start_stop, key=lambda tup: tup[0])
    return start_stop


def graph_tasks(start_stop_tups):
    start, stop = np.array(start_stop_tups).T
    plt.barh(range(len(start)), stop - start, left=start)
    plt.grid(axis="x")
    plt.ylabel("Tasks")
    plt.xlabel("Seconds")
    return plt


def connect_many_threaded_queue(addrs, num_threads=8):
    # create a queue
    q = queue.Queue()

    # add tasks to the queue
    for addr in addrs[:10]:
        q.put(addr)

    # spawn n workers
    threads = []
    while not q.empty():
        # FIXME
        addr = q.get()
        thread = threading.Thread(
            target=lambda addr: print(connect_synchronous(addr)), args=(addr,)
        )
        threads.append(thread)
        thread.start()

    # wait for all threads to finish
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    addrs = get_addrs()
    # timed(connect_many_threadpool, addrs)
    connect_many_threaded_list_with_return_vals(addrs)
