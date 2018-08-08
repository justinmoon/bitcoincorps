
# coding: utf-8

# # Recap
# 
# In the first lesson we learned to interpret the outermost layer of the Bitcoin Protocol onion: the [message structure](https://en.bitcoin.it/wiki/Protocol_documentation#Message_structure). We learned to send a `version` message to Bitcoin Network peers and listen for their `version` response. We learned to read this response and check that the correct `magic` bytes came at the beginning of the message; to interpret which of the 27 `command` types the message is; to read `payload` data associated with the command and the check the payload with a `checksum` given to us by our remote peer;
# 
# In the second lesson we learned to peel another layer or two of the onion. We learned to read the [payload](https://en.bitcoin.it/wiki/Protocol_documentation#version) of `version` messages. Along the way we had to figure out how to interpret all the sub-structures of the data, such as variable-length strings", variable-length integers, network addresses, `services` bitfields, Unix timestamps, and big-endian encoded port numbers.
# 
# We've come a long way, but we still have a long way to go.
# 
# # Getting To Know Each Other
# 
# Now that we can talk to our peers, let's be friendly neighbors and introduce ourself.
# 
# In this lesson we will connect to the nearl 10,000 Bitcoin Network peers that operate out in the open. We'll send each a `version` message and we'll record for their responses. Our first attempts at this will be far too slow and we will learn about "concurrent programming" -- a technique that frees our program to work on many things at once, in our case talking to Bitcoin Network peers.
# 
# Lastly we'll do some "data science" to find patterns in this sea of bytes. FIXME more words/
# 
# Let's get started!

# # Bitnodes
# 
# The first thing we did in the first lesson was to pull up [this website](https://bitnodes.earn.com/nodes/) and look for the IP address of some other node to talk to. 
# 
# Now we're going to write some Python code to do this for us.
# 
# bitnodes.earn.com offers [a free, unauthenticated API](https://bitnodes.earn.com/api/#list-nodes) to help us do this. You've probably heard this word before -- API -- and you probably don't know exactly what it means. The acronym [API](https://en.wikipedia.org/wiki/Application_programming_interface) stands for "Application Programming Interface". An "Application Programming Interface" is a description of how a programmer can interact with a piece of software. For example, Python has an API for converting `bytes` to `int`s: [int.from_bytes(bytes, byteorder, \*, signed=False)](https://docs.python.org/3/library/stdtypes.html#int.from_bytes). Python defines this exact function allowing programmers to accomplish this exact operation. There are multiple different "implementations" of python -- CPython, PyPy, MicroPython etc -- and they all implement this same API.
# 
# So that's the original meaning of the term "application programming interface". But it's most frequently used describe this sort of thing in a specific domain: web programming. Please read this [explainer](https://medium.freecodecamp.org/what-is-an-api-in-english-please-b880a3214a82) of this more narrow definition of the term. The [earn.com API](https://bitnodes.earn.com/api/) is one such example of "API" in this sense of the word.
# 
# The earn.com API is free and also "unauthenticated" which means we don't have to present any kind of credential in order to use this -- stock market data APIs, for one, aren't so kind!
# 
# The API has this specific [List Nodes endpoint](https://bitnodes.earn.com/api/#list-nodes) which will give a list of every node they are aware of at present or some specific point in the past. We are able to specify 
# 
# To "exercise" this API we need to send a GET http request. This is the same sort of request that your browser sense every time you load a webpage. It just fetches data.
# 
# ### cURL: A Terminal Utility
# 
# Go to your command line and type this in:
# 
# ```
# $ curl -H "Accept: application/json; indent=4" https://bitnodes.earn.com/api/v1/snapshots/latest/
# ```
# 
# (If you get any error you probably need to install the cURL program. Google it!)
# 
# This should spit a huge amoutn of "JSON" out onto your terminal. This is a complete list of all Bitcoin Network nodes which earn.com has been able to find.
# 
# ### Requests: A Python Library
# 
# This is great, but we need to find a way to do this from Python. This is where the `requests` library comes in. Watch [this video](https://www.youtube.com/watch?v=_8HPCToXdAk) to learn how to use `requests`
# 
# ##### Exercise #1: Use `requests.get` to make the same https request we made using cURL above.
# 
# Return a dictionary of the JSON response from the API 
# 
# another hint: [Relevant part](https://youtu.be/_8HPCToXdAk?t=3m12s) of Youtube video above.
# 
# hint: `.json()` get's the JSON response

# In[1]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

import os, requests, json, ipytest, requests_mock, socket, queue, random, time, multiprocessing, threading, collections
from ipaddress import ip_address
from sys import stdout
import numpy as np
import matplotlib.pyplot as plt

from ibd.two.complete import Packet, VersionMessage # get the final version ...


# In[2]:


def get_bitnodes_api_response():
    BITNODES_URL = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    ### YOUR CODE ###
    raise NotImplementedError()


# In[3]:


def get_bitnodes_api_response():
    BITNODES_URL = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    return requests.get(BITNODES_URL).json()


# In[4]:


nodes_json = open("ibd/four/response.json").read()
nodes_dict = json.loads(nodes_json)


# In[5]:


def test_get_bitnodes_api_response():
    BITNODES_URL = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    with requests_mock.mock() as mock:
        mock.get(BITNODES_URL, json=nodes_dict)
        response = get_bitnodes_api_response()
        assert response == nodes_dict

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_get_bitnodes_api_response*")


# #### Exercise #2: Call the Bitnodes API and return just the `"nodes"` part of the JSON response
# 
# hint: relevant part of the YouTube video, where you grab the value corresponding to the `name` key from the `r.json()` response JSON dictionary. We're doing the same thing in this exercise, just looking up the `nodes` key instead of the `name` key.
# ```
# r = requests.get("http://swapi.co/api/people/1")
# r.json()['name']
# ```

# In[6]:


def get_nodes():
    BITNODES_URL = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    ### YOUR CODE ###
    raise NotImplementedError()


# In[7]:


def get_nodes():
    data = get_bitnodes_api_response()
    return data['nodes']


# In[8]:


def test_get_nodes():
    BITNODES_URL = "https://bitnodes.earn.com/api/v1/snapshots/latest/"
    with requests_mock.mock() as mock:
        mock.get(BITNODES_URL, json=nodes_dict)
        nodes = get_nodes()
        assert nodes == nodes_dict['nodes']

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_get_nodes*")


# ##### Exercise #FIXME: Turn the `nodes` object into a list of `ip:port` string addresses
# 
# _Notice that the keys of the `node` object are `ip:port`_
# 
# This exercise just asks you to turn a dictionary into a list of it's keys. There's a built-in `dict` method to do this. Look it up.

# In[9]:


def nodes_to_address_strings(nodes):
    raise NotImplementedError()    


# In[10]:


def nodes_to_address_strings(nodes):
    return nodes.keys()


# In[11]:


mock_nodes = {
    "192.168.0.1:8333": {}, # ipv4
    "FE80:CD00:0:CDE:1257:0:211E:729C:8333": {}, # ipv6
}

def test_nodes_to_address_strings():
    address_strings = nodes_to_address_strings(mock_nodes)
    solution_set = {"192.168.0.1:8333", "FE80:CD00:0:CDE:1257:0:211E:729C:8333"}
    assert set(address_strings) == solution_set

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_nodes_to_address_strings*")


# ##### Exercise #FIXME: Turn the `nodes` object into a list of `(ip, port)` tuples where ip is a string and port is an integer
# 
# If you recall, [`socket.connect`](https://docs.python.org/3/library/socket.html#socket.socket.connect) takes such a tuple as its argument. This is why I want you to do this. Once we have a list of every such tuple we can iterate across it and connect to every node.
# 
# note: this is a challenging exercise
# 
# FIXME: explain this as the gameplan / objective at the beginning.

# In[12]:


def nodes_to_address_tuples(nodes):
    raise NotImplementedError()


# In[13]:


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


# In[14]:


mock_nodes = {
    "192.168.0.1:8333": {}, # ipv4
    "FE80:CD00:0:CDE:1257:0:211E:729C:8333": {}, # ipv6
}
solution_set = {
    ("192.168.0.1", 8333), 
    ("FE80:CD00:0:CDE:1257:0:211E:729C", 8333),
}

def test_nodes_to_address_tuples():
    address_tuples = nodes_to_address_tuples(mock_nodes)
    assert set(address_tuples) == solution_set

ipytest.run_tests(doctest=True)
ipytest.clean_tests("test_nodes_to_address_tuples*")


# # Calling All Nodes!
# 
# Now we have a list of address tuples -- just like the `socket.connect` API uses. Let's iterate over them and download version messages from every node.
# 
# This `get_version_message` just takes the takes what we did in lesson 2 and turns it into a function. 
# 
# `get_version_messages` iterates across every `address_tuple` in `address_tuples` (obtainable with `nodes_to_address_tuples(get_nodes())`, calls `get_version_message(address_tuple)`, stores the results and logs some information about the progress its making.

# In[15]:


OUR_VERSION = b'\xf9\xbe\xb4\xd9version\x00\x00\x00\x00\x00j\x00\x00\x00\x9b"\x8b\x9e\x7f\x11\x01\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x93AU[\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00rV\xc5C\x9b:\xea\x89\x14/some-cool-software/\x01\x00\x00\x00\x01'

def get_version_message(address_tuple):
    # FIXME Abbreviated IPv6 addresses causing errors
    sock = socket.socket()
    sock.settimeout(3) # wait 3 second for connections / responses
    try:
        sock.connect(address_tuple)
        sock.send(OUR_VERSION)
        packet = Packet.from_socket(sock)
    except Exception as e:
        print(f'Encountered "{e}" connecting to "{address_tuple}"')
        return
    version_message = VersionMessage.from_bytes(packet.payload)
    sock.close()
    return version_message
    
def get_version_messages(address_tuples):
    version_messages = []
    exceptions = []
    for address_tuple in address_tuples:
        try:
            version_message = get_version_message(address_tuple)
        except Exception as e:
            exceptions.append(e)
            continue
        version_messages.append(version_message)
        
        successes = len(version_messages)
        total = len(address_tuples)
        failures = len(exceptions)
        remaining = total - (successes + failures)
        progress = (successes + failures) / total
        print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress:.3f}% Complete")
        


# In[18]:


nodes = get_nodes()
address_tuples = nodes_to_address_tuples(nodes)
get_version_messages(address_tuples)


# After about 10 seconds of waiting for this cell to finish executing, I hope you start to wonder if our code might be running too slow? What's going on? Are we progressing? Are we stuck?
# 
# It's time to add a little logging to better understand what's happening

# In[16]:


def get_version_messages_logger(address_tuples, version_messages, exceptions, start_time):
    successes = len(version_messages)
    total = len(address_tuples)
    failures = len(exceptions)
    now = time.time()
    elapsed = now - start_time
    
    remaining = total - (successes + failures)
    progress = (successes + failures) / total
    seconds_remaining = elapsed / progress
    minutes_remaining = seconds_remaining / 60
    
    print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress:.3f}% Complete | ~{minutes_remaining:.0f} Minutes Left")

def get_version_messages(address_tuples, logger=False):
    version_messages = []
    exceptions = []
    start_time = time.time()
    for address_tuple in address_tuples:
        try:
            version_message = get_version_message(address_tuple)
        except Exception as e:
            exceptions.append(e)
            continue
        version_messages.append(version_message)
        if logger:
            logger(address_tuples, version_messages, exceptions, start_time)


# In[17]:


nodes = get_nodes()
address_tuples = nodes_to_address_tuples(nodes)
get_version_messages(address_tuples, logger=get_version_messages_logger)


# # Profiling -- Exactly Where is our Code Slow?
# 
# Do you feel like waiting around for an hour for all these version messages to download? I don't ...
# 
# In order to improve our lot, we first need to understand _why_ our code is slow. Analyzing the speed of a program is one aspect of the discipline of ["profiling"](https://en.wikipedia.org/wiki/Profiling_(computer_programming)).
# 
# To profile our slow code and understand figure out why it's so slow, we're going to use a tool called [line_profiler](https://github.com/rkern/line_profiler/). [Here is a nice tutorial](https://jakevdp.github.io/PythonDataScienceHandbook/01.07-timing-and-profiling.html) that describes a few methods of profiling python code, including line_profiler. Please read it.
# 
# To use `version_profiler` we first, we load line_profiler as an Jupyter extension. Next, we run our `get_version_message` function through it:

# In[18]:


get_ipython().run_line_magic('load_ext', 'line_profiler')


# In[19]:


get_ipython().run_line_magic('lprun', '-f get_version_message get_version_message(address_tuples[1])')


# You should see something like this at the bottom of your Jupyter window:
# 
# ![image](images/profiler.png)
# 
# If you look in the "% Time" column, you will see that the `sock.connect` and `sock.recv` (called by `Packet.from_socket`) calls are each taking up about 50% of the time. It's not because these functions are "slow" or "unoptimized" -- no, it's because they're waiting for a response from our peer; they're "blocked". And this function is blocked, the Python interpreter can't do any other work.
# 
# Concurrent programming techniques offer away around some of the problems of blocking code. They allow us to chunk our programe into bite-sized tasks which your computer switch between whenever one gets blocked, and then picking each task back up every time they are un-blocked (e.g. our peer accepts the TCP connection from `sock.connect` and it returns).
# 
# But concurrent programming (multi-threading being one approach to concurrency) can be very difficult:
# 
# ![image](./images/this-tall.jpg)
# 
# We'll need concurrency, however, when we write our initial-block-downloader, so let's dip our toes into Python concurrency.
# 
# Please read [this tutorial](https://code.tutsplus.com/articles/introduction-to-parallel-and-concurrent-programming-in-python--cms-28612), and stop at the "Gevent" section. You'll learn to write a concurrent web-scraper using multiple "threads" and multiple "processes". And take note: the `get_version_messages` function we're trying to speed up is basically a web scraper. Try to anticipate how these techniques apply to our situation. Can you write a multi-threaded or multi-process `get_version_messages` function?
# 
# FIXME warn about the list comprehensions
# 
# ### Translating The Tutorial
# 
# This is kind of the key block of code from the tutorial
# 
# ![image](images/run-tasks.png)
# 
# Let's translate it into out problem space.

# In[20]:


def base_logger():
    print(f"PID: {os.getpid()} | Process Name: {multiprocessing.current_process().name} | Thread Name: {threading.current_thread().name}")

def with_logger(func, logger):
    def wrapped(*args, **kwargs):
        logger()
        return func(*args, **kwargs)
    return wrapped

def synchronous(target, addresses):
    for address in addresses:
        target(address)
        
def multithreaded(target, addresses):
    threads = []
    # create the threads
    for address in addresses:
        thread = threading.Thread(target=target, args=(address,))
        threads.append(thread)
    # start the threads
    for thread in threads:
        thread.start()
    # wait for all to finish
    for thread in threads:
        thread.join()
    end_time = time.time()
  
def multiprocess(target, addresses):
    processes = []
    # create the processes
    for address in addresses:
        process = multiprocessing.Process(target=target, args=(address,))
        processes.append(process)
    # start the processes
    for process in processes:
        process.start()
    # wait for all to finish
    for process in processes:
        process.join()

def logging_demo(addresses, logger):
    target = with_logger(get_version_message, logger)
    for func in [synchronous, multithreaded, multiprocess]:
        start = time.time()
        func(target, addresses)
        stop = time.time()
        print(f'"{func.__name__}()" took {stop - start} seconds')


# In[21]:


# FIXME kill this cell
nodes = get_nodes()
address_tuples = nodes_to_address_tuples(nodes)


# In[22]:


i = random.randint(0, 9000)
logging_demo(address_tuples[i:i+4], base_logger)


# Looks at that!
# 
# Using the same code from the tutorial we are able to speed up our function 3 times!
# 
# Take note:
# * The the first block of code runs entirely within the same "MainProcess" and "MainThread"
# * The second, threaded block of code runs entirely within the "MainProcess" but within 4 different threads attached to that "MainProcess".
# * The third, multi-process block of code spawns executes across 4 different process, but within each process the code executes in the "MainThread"
# * Lastly, not that the multi-threaded version is a little faster than the multi-process version. This is because threads are a little "lighter weight" than processes so they start faster, and we aren't doing any CPU-intensive number crunching where multi-processing is able to spread the work across the multiple cores of your laptop.
# 
# 
# But it isn't all good. This code has a very nasty bug hidden inside.
# 
# 
# # Race Conditions
# 
# If you run the `demo` function enough times you may notice that the printing gets messed up. This bug has occurred in the image below. The third line of the "threading" section contains two messages, but the fourth line is empty! This is because the different threads might print at exactly the same time, making their output interfere. This is called a "race condition", and it's the worst enemy of the multi-threaded program. If you'd like to learn more, check out [this phenominal talk on concurrency by Python core contributer Raymond Hettinger](https://www.youtube.com/watch?v=Bv25Dwe84g).
# 
# ![image](images/race-conditions.png)
# 
# We'll use a technique covered in the video to demonstrate how to make the race conditions worse. If we put tiny little `time.sleep` calls in our code, things no longer happen in the order we were expecting.
# 
# TODO: more explanation of why this breaks
# 
# ### Fuzzing Shatters Our Multithreaded & Multiprocess Code

# In[23]:


# FIXME print-based fuzzing breaks threads but not processes
# stdout.write breaks processes
# FIXME contact raymond hettinger about this
# perhaps .join

def fuzz():
    time.sleep(random.random() / 10)


def fuzz_logger():
    fuzz()
    stdout.write(f"PID: {os.getpid()} | ")
    stdout.flush()
    fuzz()
    stdout.write(f"Process Name: {multiprocessing.current_process().name} | ")
    stdout.flush()
    fuzz()
    print(f"Thread Name: {threading.current_thread().name}", end="\n")
    
# def fuzz_logger():
#     print(f"PID: {os.getpid()}", end=" | ")
#     fuzz()
#     print(f"Process Name: {multiprocessing.current_process().name}", end=" | ")
#     fuzz()
#     print(f"Thread Name: {threading.current_thread().name}", end="\n")


# In[24]:


print("Threaded code easily owned by race conditions")
print("=============================================")
print()

logging_demo(address_tuples[71:75], fuzz_logger)


# See how nicely the normal, synchronous code prints its little log statements?
# 
# See how *the exact same logging code* produces unreadable output when run in different threads?
# 
# How can we fix it?
# 
# ### Queues To The Rescue, Again
# 
# The answer is to only let one thread print -- the `MainThread`. We can accomplish this by having our logger send every message to the main thread via a simple "queue" instead of printing it. All we need to do is create a `queue.Queue` object and call `.put(message)` to make our message accessible by the main thread, which just needs to call `.get()` on the `queue.Queue` instance to pull out one message. The main thread will do this and print the result until the queue runs dry -- which will result in a `queue.Empty` exception being raised.
# 
# Python's `queue.Queue` takes special care to ensure that synchonization bugs (like the one above) can't happen.
# 
# Queues are pretty easy to use. We create separate `queue.Queue` instances for each type of data we want to send from inside the threads to the main thread. Whenever we want to send this sort of data from inside the thread to the main thread, we call `.put()` ont the relevant queue instance. This just drops a message into the queue, where it sits until the main thread retrieves it for further processing. In our case, we'll put `(start, stop)` tuples into the queue representing the time that that the thread started and stopped execution. When the main thread pulls out all these tuples, it will plot these intervals on a graph (`graph_intervals`) to give us a sense of how differently our synchronous and asynchronous code execute.

# In[25]:


log_queue = queue.Queue()

def better_logger():
    log_queue.put(f"PID: {os.getpid()} | Process Name: {multiprocessing.current_process().name} | Thread Name: {threading.current_thread().name}")

def retrieve(q):
    while True:
        try:
            yield q.get(timeout=1)
        except queue.Empty:
            break
    
def multithreaded(target, addresses):
    threads = []
    # create the threads
    for address in addresses:
        thread = threading.Thread(target=target, args=(address,))
        threads.append(thread)
    # start the threads
    for thread in threads:
        thread.start()
    # wait for all to finish
    for thread in threads:
        thread.join()
    messages = retrieve(log_queue)
    for message in messages:
        print(message)
    


# In[26]:


print("Queues helps eliminate race conditions in concurrent code")
print("=========================================================")
target = with_logger(get_version_message, better_logger)
multithreaded(target, address_tuples[20:24])


# ### Profiling With Graphs
# 
# As we say in the last section, queues allow us to extract values from the short-lived "task threads" / processes and send them back to the long-lived, parent "main thread" in a reliable way. In the previous section we used it for logging strings, but we can use this technique to transmit any sort of data we like. In this section we will use them to fill out a graph of the execution duration of every `get_version_message` call we make.
# 
# ```
# 
# In order to do so, we will need to note when each task begins and when it ends. Not only that, but we will need to pull these values our of the thread. This isn't quite so easy. Python doesn't have anything `thread.value()` which will produce some kind of "return value" from the thread or process.
# 
# ```
# 

# In[26]:


def graph_intervals(intervals):
    start, stop = np.array(intervals).T
    plt.barh(range(len(start)), stop-start, left=start)
    plt.grid(axis="x")
    plt.ylabel("Tasks")
    plt.xlabel("Seconds")
    plt.show()
    
def timed(func, q):
    def wrapped(*args, **kwargs):
        start = time.time()
        val = func(*args, **kwargs)
        stop = time.time()
        q.put((val, start, stop))
    return wrapped

def graph_demo(addresses):
    sq = queue.Queue()
    tq = queue.Queue()
    pq = multiprocessing.Queue()
    
    funcs_and_qs =  [(synchronous, sq), (multithreaded, tq), (multiprocess, pq)]
    for func, q in funcs_and_qs:
        target = timed(get_version_message, q)
        func(target, addresses)        
    
    for _, q in funcs_and_qs:
        thing = retrieve(q)
        intervals = [(start, stop) for _, start, stop in thing]
        graph_intervals(intervals)


# In[31]:


i = random.randint(0, 9000)
graph_demo(address_tuples[i:i+30])


# That's pretty cool. 
# 
# When I run it, there are one or two very slow multithreaded and multiprocess tasks which take 5 times longer than the rest. If we ignore these slow tasks, the concurrent code takes about 1/2 second on my machine. While the Synchronous code takes 10 seconds. That a 20x speedup in the best case. A few slow tasks won't be able to slow down our code too much becase the socket connections will time out in a few seconds. Plus, the fast tasks don't have to wait around for the "blocked" tasks in a concurrent environment. This is vital!

# # I want it all
# 
# let's see how long it takes to download everything. Remember the ETA's you were getting when we first tried this. My ETA was about 45 minutes ...

# In[27]:




def get_version_messages_threaded(address_tuples):
    version_messages = []
    exceptions = []
    for address_tuple in address_tuples:
        try:
            version_message = get_version_message(address_tuple)
        except Exception as e:
            exceptions.append(e)
            continue
        version_messages.append(version_message)
        
        successes = len(version_messages)
        total = len(address_tuples)
        failures = len(exceptions)
        remaining = total - (successes + failures)
        progress = (successes + failures) / total
        print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress:.3f}% Complete")

        
def get_version_message(address_tuple):
    # FIXME Abbreviated IPv6 addresses causing errors
    
    # FIXME
    ipv4 = ip_address(address_tuple[0]).version == 4
    param = socket.AF_INET if ipv4 else socket.AF_INET6
    
    sock = socket.socket(param, socket.SOCK_STREAM)
    sock.settimeout(7) # wait 3 second for connections / responses
    sock.connect(address_tuple)
    sock.send(OUR_VERSION)
    packet = Packet.from_socket(sock)
    version_message = VersionMessage.from_bytes(packet.payload)
    sock.close()
    return version_message
        
def putting(func, q):
    def wrapped(*args, **kwargs):
        val = exc = None
        try:
            val = func(*args, **kwargs)
        except Exception as e:
            exc = e
        q.put((val, exc))
    return wrapped
        
def get_version_messages_threaded(addresses):

    q = queue.Queue()
    threads = []
    version_messages = []
    exceptions = []
    
    target = putting(get_version_message, q)
    
    # create the threads
    for address in addresses:
        thread = threading.Thread(target=target, args=(address,))
        threads.append(thread)
    # start the threads
    for thread in threads:
        thread.start()
    # don't wait for them to finish, just start reading results from q
    # wait for all to finish
#     for thread in threads:
#         thread.join()
    messages = retrieve(q)
    for version_message, exception in messages:
        # todo: have a namedtuple "task result", so i can return version messages and exceptions
        if version_message is not None:
            version_messages.append(version_message)
        if exception is not None:
            exceptions.append(exception)
        successes = len(version_messages)
        total = len(addresses)
        failures = len(exceptions)
        remaining = total - (successes + failures)
        progress = (successes + failures) / total
        print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress:.3f}% Complete")
        
    return version_messages, exceptions


# In[110]:


version_messages, exceptions = get_version_messages_threaded(address_tuples)


# In[34]:


for e in exceptions:
    print(e)


# In[36]:


e = exceptions[0]


# In[ ]:


e.


# In[31]:


counter = collections.Counter([
    str(e) for e in exceptions
])
counter.most_common()


# # Workers

# In[28]:


def make_worker(func, in_q, out_q):
    def wrapped():
        while not in_q.empty():
            val = exc = None
            task = in_q.get()
            try:
                val = func(task)
            except socket.gaierror as e:
                exc = e
                print("gai on ", task)
            except Exception as e:
                exc = e
            out_q.put((val, exc, task))       
    return wrapped

def get_version_messages_threaded(addresses, num_workers=8):
    result_queue = queue.Queue()
    address_queue = queue.Queue()
    workers = []
    version_messages = []
    exceptions = []
    
    target = make_worker(get_version_message, address_queue, result_queue)
    
    for address in addresses:
        address_queue.put(address)
    
    # create the workers
    
    for address in range(num_workers):
        worker = threading.Thread(target=target)
        workers.append(worker)
    # start the workers
    for worker in workers:
        worker.start()
        
    messages = retrieve(result_queue)
    for version_message, exception, address in messages:
        # todo: have a namedtuple "task result", so i can return version messages and exceptions
        if version_message is not None:
            version_messages.append(version_message)
        if exception is not None:
            exceptions.append((exception, address))
        successes = len(version_messages)
        total = len(addresses)
        failures = len(exceptions)
        remaining = total - (successes + failures)
        progress = (successes + failures) / total
        if remaining % 500 == 0:
            print(f"{successes} Received | {failures} Failures | {remaining} Remaining | {progress:.3f}% Complete")
        
    return version_messages, exceptions


# In[114]:


version_messages, exceptions = get_version_messages_threaded(address_tuples)


# In[116]:


counter = collections.Counter([
    str(e) for e in exceptions
])
counter.most_common()


# In[51]:


fam = [e for e in exceptions if str(e) == '[Errno -9] Address family for hostname not supported']


# In[52]:


f = fam[0]


# In[117]:


vm=get_version_message(("104.131.103.106", 8333))
vm


# In[72]:


ip.version


# In[37]:


exceptions[0]


# In[38]:


address_tuples


# In[39]:


from ipaddress import ip_address


# In[41]:


ip = ip_address("2002:3e92:46d8::3e92:46d8")
ip


# In[44]:


ip_address('95.216.154.242').exploded


# # Workers Graphed 

# In[40]:


def make_worker(func, in_q, out_q):
    def wrapped():
        while not in_q.empty():
            start = time.time()
            val = exc = None
            task = in_q.get()
            try:
                val = func(task)
            except socket.gaierror as e:
                exc = e
#                 print("gai on ", task)
            except Exception as e:
                exc = e
            stop = time.time()
            out_q.put((val, exc, task, start, stop))       
    return wrapped


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
#             graph_intervals(intervals)
            
    for worker in workers:
        worker.join()

    return version_messages, exceptions, intervals


# In[43]:


version_messages, exceptions, intervals = get_version_messages_threaded_graphed(address_tuples, num_workers=20)


# # Worker Threads
# 
# 

# Downloader TODO
# * make a short list of known-good, always up nodes from the bitnodes leaderboard. use these for the little demos.
# * Make an example with n workers ... what number of n is fastest?
# * (optional) given an example of a cpu-intensive task where multipprocessing excels (fib in a nod to David Beazley?)
# 
# Conclusion
# * some of this may have seemed like a bit of a needless tangent, but I assure it was not. When we finally implement our intial-block-downloader we will need to stay connected to many peers at the same time and concurrently download blocks from each of them. Our code must not have race conditions, and it must have a central, controlling task manager that can supervise the connections to our peers and assemble valid blockchain. We will spend a lot of time profiling and optimizing our code because initial block download must be as fast as possible.
# 
# Homework:
# * Make some kind of graphical representation of the data we receive from our peers
# * This is the bitnodes crawler: https://github.com/ayeowch/bitnodes. Try to write your own. This would simply involve connecting to a peer, sending them a `getaddr` message, listening for the `addr` response, then doing the verack handshake with each address contained in the `addr` message, and repeat -- taking care to log each version message you receive. Not that bitnodes skips any nodes running versions < 70001. Can you find some nodes with lower version numbers than that?
# * A related idea to the above idea -- what if you sent `getaddr` messages to every peer that bitnodes gave us, listened for and saved the convents of each peer's `addr` response. Then you see if our peers will tell us about any nodes that bitnodes doesn't includ -- this is probably the best approach to find old nodes.
# 
# Data Science TODO
# * 
