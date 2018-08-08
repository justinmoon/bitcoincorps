
# coding: utf-8

# In[2]:


get_ipython().run_line_magic('load_ext', 'line_profiler')
get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

import os, requests, json, ipytest, requests_mock, socket, queue, random, time, multiprocessing, threading, collections
from ipaddress import ip_address
from sys import stdout
import numpy as np
import matplotlib.pyplot as plt

from ibd.two.complete import Packet, VersionMessage # get the final version ...


# In[3]:


def get_nodes():
    url = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    response = requests.get(url)
    return response.json()["nodes"]

def nodes_to_address_tuples(nodes):
    address_strings = nodes.keys()
    address_tuples = []
    for address_string in address_strings:
        ip, port = address_string.rsplit(":", 1)
        
        # FIXME
        ip = ip.replace('[','').replace(']','')
        
        address_tuple = (ip, int(port))
        address_tuples.append(address_tuple)
    return address_tuples

def get_addresses():
    nodes = get_nodes()
    address_tuples = nodes_to_address_tuples(nodes)
    return address_tuples


# In[34]:


OUR_VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

def make_worker(func, in_q, out_q):
    def wrapped():
        while True:
            start = time.time()
            val = exc = None
            try:
                # slightly larger than socket timeout
                # timing-out tasks tend to bunch up at the very end
                # you need to wait for the timout errors to raise
                # in order to process every task
                task = in_q.get(3.5)
            except queue.Empty:
                break
            try:
                val = func(task)
            except Exception as e:
                exc = e
            stop = time.time()
            out_q.put((val, exc, task, start, stop))       
    return wrapped

def graph_intervals(intervals):
    start, stop = np.array(intervals).T
    plt.barh(range(len(start)), stop-start, left=start)
    plt.grid(axis="x")
    plt.ylabel("Tasks")
    plt.xlabel("Seconds")
    plt.show()

def retrieve(q):
    while True:
        try:
            yield q.get(timeout=1)
        except queue.Empty:
            break

def get_version_messages_logger(address_tuples, version_messages, exceptions, start_time):
    successes = len(version_messages)
    total = len(address_tuples)
    failures = len(exceptions)
    now = time.time()
    elapsed = now - start_time
    
    remaining = total - (successes + failures)
    progress = (successes + failures) / total
    rate = (successes + failures) / elapsed
    seconds_remaining = remaining / rate
    minutes_remaining = seconds_remaining / 60
    
    print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress*100:.3f}% Complete | ~{minutes_remaining:.1f} Minutes Left")

            
def get_version_message(address_tuple):
    # FIXME Abbreviated IPv6 addresses causing errors
    
    # FIXME
    ipv4 = ip_address(address_tuple[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    
    sock = socket.socket(param, socket.SOCK_STREAM)
    sock.settimeout(3) # wait 3 second for connections / responses
    sock.connect(address_tuple)
    sock.send(OUR_VERSION)
    packet = Packet.from_socket(sock)
    version_message = VersionMessage.from_bytes(packet.payload)
    sock.close()
    return version_message

def get_version_messages_threaded_graphed(addresses, num_workers=1000):
    start_time = time.time()
    result_queue = queue.Queue()
    address_queue = queue.Queue()
    workers = []
    version_messages = []
    exceptions = []
    intervals = []
    
    target = make_worker(get_version_message, address_queue, result_queue)
    
    for address in addresses:
        address_queue.put(address)
    
    # create the workers
    for _ in range(num_workers):
        worker = threading.Thread(target=target)
        workers.append(worker)
    # start the workers
    for worker in workers:
        worker.start()
        
    messages = retrieve(result_queue)
    for version_message, exception, address, start, stop in messages:
        # todo: have a namedtuple "task result", so i can return version messages and exceptions
        intervals.append([start, stop])
        if version_message is not None:
            version_messages.append(version_message)
        if exception is not None:
            exceptions.append((exception, address))

        # FIXME code duplicated inside     
        # maybe i can pass some `every=1` kwarg where you can cut down on the logging outputs ...
        successes = len(version_messages)
        total = len(addresses)
        failures = len(exceptions)
        remaining = total - (successes + failures)
        
        if remaining % 50 == 0:
            get_version_messages_logger(addresses, version_messages, exceptions, start_time)
        if remaining % 500 == 0:
            graph_intervals(intervals)
    print(remaining)
    print(len(version_messages) + len(exceptions))
    for worker in workers:
        worker.join()

    return version_messages, exceptions, intervals


# In[35]:


# define the addresses if they aren't defined
try:
    addresses
except:
    addresses = get_addresses()


# In[ ]:


version_messages, exceptions, intervals = get_version_messages_threaded_graphed(addresses[:1000], num_workers=20)


# In[29]:


get_ipython().run_line_magic('lprun', '-f get_version_messages_threaded_graphed get_version_messages_threaded_graphed(addresses[:10], num_workers=20)')

