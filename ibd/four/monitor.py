def queued_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE worker_start IS NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def completed_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE version_payload IS NOT NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def failed_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE error IS NOT NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def total_count(db):
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def started_count(db):
    # start time + worker non empty, worker_stop empty
    result = db.execute(
        """
        SELECT COUNT(*) FROM addresses
        WHERE worker_start IS NOT NULL
            AND worker_stop IS NULL
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def crawler_start_time(db):
    result = db.execute(
        """
        SELECT MIN(worker_start)
        FROM addresses
    """
    ).fetchone()
    result = result[0]  # FIXME
    return result


def worker_statuses(db):
    # TODO: also query count(*) and display that ...
    q = """
    SELECT 
        worker, ip, strftime('%s','now') - MAX(worker_start)
    FROM 
        addresses
    WHERE 
        worker IS NOT NULL 
        AND worker_stop IS NULL
    GROUP BY 
        worker
    """
    result = db.execute(q).fetchall()
    return sorted(result, key=lambda r: -int(r[0].split("-")[1]))
    # result = db.execute(q).fetchall()
    # addresses = [Address(*args) for args in result]
    # return sorted(addresses, key=lambda address: int(address.worker.split("-")[1]))


def crawler_report():
    headers = ["Queued", "Completed", "Failed"]
    rows = [[queued_count(db), completed_count(db), failed_count(db)]]
    return tabulate(rows, headers)


# TODO https://twitter.com/brianokken/status/1029880505750171648
def worker_report():
    headers = ["Worker Name", "Peer Address", "Elapsed"]
    rows = worker_statuses(db)
    return tabulate(rows, headers)


def report():
    c = crawler_report()
    length = len(c.split("\n")[0])
    padding_len = round((length - 7) / 2)
    padding = " " * padding_len
    print(padding + "===========" + padding)
    print(padding + "| Crawler |" + padding)
    print(padding + "===========" + padding)
    print()
    print(c)

    print("\n\n")

    print(worker_report())
