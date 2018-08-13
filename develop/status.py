from collections import Counter

from tinydb import Query, TinyDB

pdb = TinyDB("db.json")

payloads = pdb.all()

report = Counter([p["type"] for p in payloads]).most_common()
errors = Counter([p["data"] for p in payloads if p["type"] == "error"]).most_common()

print(report)
print(errors)
