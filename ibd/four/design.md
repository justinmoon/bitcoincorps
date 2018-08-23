# GOAL: something very simple

Questions:
* do we need the queues?

###  do we need the queues?

What they're used for:
* communicating addresses / tasks to workers
* communicating task results (payloads, new addresses, execution times, errors) to parent crawler
    * SQLite is thread-safe, so this isn't necessary strictly speaking ... we could just commit to db from threads ...

How we could replace them:
* have one sqlite table containing addresses. have some way of determining wihch addresses have been contacted and which have not. workers read from it to find next task, write to it when they receive new addres. unique constraint on (ip, port) so we don't have duplicates. perhaps we can have sqlite just ignore (https://sqlite.org/lang_conflict.html) using "OR" command when we attempt to add new addresses from "addr" messages. 
* the main thread wouldn't have much to do ...

### Abstractions

Should we have the "task" abstraction? What do we gain from it?

Is there a clean way to attempt "retries"?

Should we store raw or parsed version / addr messages -- or both)?

##### v1

Address Attributes:
* ip
* port
* connection_start
* connection_stop
* connection_error
* version_payload
* addr_payload

##### v2

Address Attributes:
* ip
* port

Address Relationships
* Connection

Connection Attributes
* error
* start
* stop

Connection Relationships
* Version Message
* Addr Message
    * More `Address` rows
* Worker

non-empty Connection.start and empty Connectin.stop can be used to link workers to active connectinos

### DB api

next_address()

save_addresses(addresses)
save_connection(c)
save_version_payload(vp)
save_addrs_payload(ap)

num_tasks_attempted()
num_tasks_failed()
num_tasks_succeeded()
earliest_start_time()

worker_report()
    * 3 way join between worker / connection / address to get worker name / start time / ip

### Ideas

Create a new sqlite db for every run unless specifically directed to resuse by cli args

### Class Ideas

the first version of this should use a thread-safe queue to keep track of addresses

second version moves everything to sqlite, once it's introduced ...
