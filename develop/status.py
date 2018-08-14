import time
from collections import Counter
from pprint import pprint

from tabulate import tabulate
from tinydb import Query, TinyDB

db = TinyDB("db.json")


def started(task):
    return task["start"] is not None


def pending(task):
    return not completed(task)


def completed(task):
    return task["addr_payload"] is not None


def get_started(tasks):
    return [task for task in tasks if started(task)]


def get_pending(tasks):
    return [task for task in tasks if pending(task)]


def get_completed(tasks):
    return [task for task in tasks if completed(task)]


def one_and_done(task):
    return completed(task) and len(task["errors"]) == 0


def one_and_done_percentage(tasks):
    started = get_started(tasks)
    one_and_dones = [task for task in tasks if one_and_done(task)]
    number = len(one_and_dones) / len(started)
    return percentage(number)


def get_start_time(tasks):
    started = [task for task in tasks if task["start"] is not None]
    if not started:
        return -1  # FIXME
    return min([task["start"] for task in started])


def get_end_time(tasks):
    started = [task for task in tasks if task["start"] is not None]
    if not started:
        return -1  # FIXME
    return max([task["start"] for task in started])


def completed_per_second(tasks, interval):
    start_time, end_time = interval
    elapsed = end_time - start_time
    num_completed = len(get_completed(tasks))
    return num_completed / elapsed


def tasks_completed(tasks):
    completed = get_completed(tasks)
    return len(completed)


def get_batch(tasks):
    return max([task["batch"] for task in tasks])


def percentage(value):
    return f"{value:.2%}"


### Warning: don't implement any of the below code if it wouldn't be useful with sqlite too ...

###############
### history ###
###############

query = Query()

all_tasks = db.search(query["type"] == "task")
highest_batch = get_batch(all_tasks)

tasks_by_batch = {
    batch_: [task for task in all_tasks if task["batch"] == batch_]
    for batch_ in range(highest_batch)
}

intervals_by_batch = {
    batch: (get_start_time(tasks), get_end_time(tasks))
    for batch, tasks in tasks_by_batch.items()
}


headers = ["Batch", "Start Time", "# Completed", "One-And-Done %", "Completed / Second"]
rows = [
    [
        get_batch(tasks),
        get_start_time(tasks),
        len(get_completed(tasks)),
        one_and_done_percentage(tasks),
        completed_per_second(tasks, intervals_by_batch[batch]),
    ]
    for batch, tasks in tasks_by_batch.items()
    if len(tasks) > 1  # FIXME
]

print(tabulate(rows, headers))


###############
### current ###
###############

# first line is ^^ for just this task

# length-of-queue |

# percentage distributeion of different errors

# version number breakdown

# services breakdown
