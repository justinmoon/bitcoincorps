
# coding: utf-8

# # Let's Parse 1000 Version Messages From Real Bitcoin Nodes
# 
# So it seems like we correctly translated all the relevant tables from the protocol documentation into Python code. But how can we be sure we didn't make any mistakes. We can probably never be completely sure, but a good way for us to get started would be to send `version` messages to a large number of Bitcoin nodes, listen for and decode their `version` replies using `VersionMessage` classmethods and seeing if things "make sense".
# 
# `earn.com` offers [a free, unauthenticated API](https://bitnodes.earn.com/api/#list-nodes) where you can get a list of all visible Bitcoin full nodes.
# 
# Execute this command in your terminal to see what kind of data this API gives us:
# 
# ```
# curl -H "Accept: application/json; indent=4" https://bitnodes.earn.com/api/v1/snapshots/latest/
# ```
# 
# We can call this API directly from Python using the `requests` module:

# In[ ]:


import requests
from pprint import pprint

def get_nodes():
    url = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    response = requests.get(url)
    return response.json()["nodes"]


# In[ ]:


nodes = get_nodes()
pprint(nodes)


# In particular, we can get a list of addresses using the `nodes.keys()`:

# In[ ]:


def get_addr_tuples():
    nodes = get_nodes()
    raw_addrs = nodes.keys()
    addr_tuples = []
    for raw_addr in raw_addrs:
        ip, port = raw_addr.rsplit(":", 1)
        addr_tuple = (ip, int(port))
        addr_tuples.append(addr_tuple)
    return addr_tuples

addr_tuples = get_addr_tuples()
print(addr_tuples)


# In[ ]:


import downloader

downloader.cleanup()
addrs = downloader.get_addr_tuples()
downloader.connect_many(addrs)


# Do you notice how slow this is?
# 
# My machine received 9513 addresses from earn.com, and is processes about 5 messages per second. This is going to take about 30 seconds to process everything. 
# 
# TOO SLOW!!!
# 
# Now let's thing for a second. Why's it so slow? In fact, it's because we're spending almost all our time waiting for `sock.connect` or `sock.recv` to give us a return value. Our Python program is just sitting on its hands while packets fly across the world, one at a time.
# 
# Isn't there something we could have our Python program work on while it waits? Couldn't we perhaps have it send a few messages at a time?
# 
# The answer, or course, is "yes". But this requires "asynchronous programming". FIXME: insert youtube link
# 
# I'm not going to attempt to fully explain how this works, but I'll once again give you a magical program that does what we want.

# In[ ]:


import downloader

downloader.cleanup()
addrs = downloader.get_addr_tuples()
downloader.async_connect_many(addrs)


# So what the hell is going on here?
# 
# These strings don't look like port numbers, and 

# In[ ]:


from collections import Counter
from library import VersionMessage, Address

def get_versions():
    with open('versions.txt', 'rb') as f:
        lines = f.readlines()
        lines[:] = (value.strip() for value in lines if value != b'\n')
        return lines


# In[ ]:


from collections import Counter

vms = []

for raw in get_versions():
    try:
        vm = VersionMessage.from_bytes(raw)
        vms.append(vm)
    except Exception as e:
        print(e)
        continue


# In[ ]:


len(vms)


# In[ ]:


for vm in vms:
    print(vm.addr_recv)


# In[ ]:


ports_counter = Counter([addr.port for addr in addrs])
ports_counter.most_common(10)


# In[ ]:


ip_counter = Counter([addr.ip for addr in addrs])
ip_counter.most_common(10)


# In[ ]:


ips = Counter([addr.formatted_ip for addr in addrs])
ips


# I get 
# 
# ```
# {IPv4Address('104.5.61.4'), IPv4Address('198.27.100.9')}
# ```
# 
# '104.5.61.4' is my public ip address
# 
# 

# In[ ]:


# all 53 which report 8333 also report the wrong ip address ...
set([interpret_raw_ip(addr.ip) for addr in addrs if addr.port == 8333])


# In[ ]:


raw_wrong_ip = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xc6\x1bd\t'

for line in get_versions():
    try:
        vm = VersionMessage.from_bytes(line)
        if vm.addr_recv.ip == raw_wrong_ip:
            print(vm.user_agent)
    except:
        continue


# So there's something funky goin gon with that version of the bitcoin software. I would guess that it's hardcoding the port and ip. The reason I'm guessing it's hardcoded is because 8333 is the port that bitcoin core runs on. 
# 
# But not all node reporting this user agent get my ip / port wrong:

# In[ ]:


satoshi_16_user_agent = b'/Satoshi:0.16.0/'

for line in lines:
    try:
        vm = VersionMessage.from_bytes(line)
        a = Address.from_bytes(vm.addr_recv, version_msg=True)
        if vm.user_agent == satoshi_16_user_agent:
            print(interpret_raw_ip(a.ip), a.port)
    except:
        continue


# At this point I think we can be reasonably confident that we've figured out how to parse ip addresses. But along the way it seems that we've also learned to not trust them!

# In[ ]:


right_ip = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xffh\x05=\x04'

formatted = ":".join([str(b) for b in right_ip[-4:]])

formatted


# # comparing speeds / new code

# In[ ]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# In[ ]:


from ibd.four.downloader import *


# In[ ]:


addrs = get_addrs()
print(f"got {len(addrs)} node addresses")


# In[ ]:


fifty_addrs = addrs[:50]
futures = connect_many_threadpool(fifty_addrs)
start_stop_tups = futures_to_start_stop_tups(futures)


# In[ ]:


futures = list(futures)
futures


# In[ ]:


results = [f.result() for f in futures if not f.exception()]


# In[ ]:


start_stop = [(start, stop) for (msg, start, stop) in results]


# In[ ]:


start_stop = sorted(start_stop, key=lambda tup: tup[0])
start_stop


# In[ ]:


import numpy as np
import matplotlib.pyplot as plt

start,stop = np.array(start_stop).T
plt.barh(range(len(start)), stop-start, left=start)
plt.grid(axis="x")
plt.ylabel("Tasks")
plt.xlabel("Seconds")


# # Execute tasks in threadpool and graph results

# In[ ]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# In[ ]:


from ibd.four.downloader import *

addrs = get_addrs()
print(f"got {len(addrs)} node addresses")

fifty_addrs = addrs[:200]
futures = connect_many_threadpool(fifty_addrs)
start_stop_tups = threadpool_result_to_start_stop_tups(futures)
graph_tasks(start_stop_tups)


# NOTES
# * "to event loop, or not to event loop"
# * should i split the concurrency lesson into 2 -- teach some here and some during the "download blocks from multiple peers" 
