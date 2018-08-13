from tinydb import Query, TinyDB

pdb = TinyDB('db.json')
edb = TinyDB('errors.json')

payloads = pdb.all()
errors = edb.all()

print(f"#errors={len(errors)}")
print(f"#payloads={len(payloads)/2}")

