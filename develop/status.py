import time
from collections import Counter
from pprint import pprint

from tinydb import Query, TinyDB

db = TinyDB("db.json")


# report = Counter([p[""] for p in payloads]).most_common()
# failures = Counter([p["errors"] for p in payloads if p["type"] == "error"]).most_common()


# print([e["id"] for e in tasks])

# pprint(
# [
# {
# "failures": len(t["errors"]),
# "errors": list(set([e[0] for e in t["errors"]])),
# "status": "done" if t["addr_payload"] else "pending",
# }
# for t in tasks
# ]
# )


def task_started(task):
    return task["start"] is not None


def get_started(tasks):
    return [task for task in tasks if task_started(task)]


def task_completed(task):
    return task["addr_payload"] is not None


def get_completed(tasks):
    return [task for task in tasks if task_completed(task)]


# FIXME: make a "failure" status so that we can grab the failed tasks


def task_pending(task):
    return not task_completed(task)


def get_pending(tasks):
    return [task for task in tasks if task_pending(task)]


def task_completed_first_try(task):
    return task_completed(task) and len(task["errors"]) == 0


def completed_first_try_percentage(tasks):
    started = get_started(tasks)
    completed_first_try = [task for task in tasks if task_completed_first_try(task)]
    return len(completed_first_try) / len(started)


def get_start_time(tasks):
    started = [task for task in tasks if task["start"] is not None]
    return min([task["start"] for task in started])


def completed_per_second(tasks):
    start_time = get_start_time(tasks)
    elapsed = time.time() - start_time
    num_completed = len(get_completed(tasks))
    return num_completed / elapsed


def tasks_completed(tasks):
    completed = get_completed(tasks)
    return len(completed)


def get_current_run(tasks):
    return max([task["batch"] for task in tasks])


### Warning: don't implement any of the below code if it wouldn't be useful with sqlite too ...

###############
### history ###
###############

# run-number | start-time | first-time-success % | total-contacted | time-per-success |

query = Query()

all_tasks = db.search(query["type"] == "task")
batch = get_current_run(all_tasks)

_tasks = current_run = db.search(query["type"] == "task" and query["batch"] == batch)

print(set([task["batch"] for task in _tasks]))

history_string = f"{get_current_run(_tasks)}th running | {get_start_time(_tasks)} start time | {len(get_completed(_tasks))} completed |{completed_first_try_percentage(_tasks):.0%} in one try | {completed_per_second(_tasks)} completed per second"
print(history_string)


###############
### current ###
###############

# first line is ^^ for just this task

# length-of-queue |

# percentage distributeion of different errors

# version number breakdown

# services breakdown
