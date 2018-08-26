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

Version Message
* Same as currently, but keep the raw bytes

Addr Message
* Same as currently, but keep the raw bytes



### DB api

save_connection()
-> Adds entry to "connections" table
-> Adds entry to "version_messages" table
-> Adds entry to "addr_messages" table
-> (?) Adds entry to the "errors" table

Would you ever update a connection, version_message, or addr_message entry in the database?

### Ideas

Create a new sqlite db for every run unless specifically directed to resuse by cli args

Maybe connection.send would just take messages and wrap them in `Packet`?

### Class Ideas

the first version of this should use a thread-safe queue to keep track of addresses

second version moves everything to sqlite, once it's introduced ...

# Round Up

Problems
* if we get the same address from 2 different peers, we have a problem
* cpu utilization spirals out of control
* workers die if the queue is ever empty ... this is a very good argument for using an actual queue
* \_connect is very ugly
* no worker report

"Network is Unreachable" seems to happen more frequently when many threads all try to make connections concurrently ...

