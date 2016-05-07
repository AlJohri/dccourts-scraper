import pymongo, csv

client = pymongo.MongoClient()
db = client.dccourts

fieldnames = ['id', 'case_type', 'party', 'party_type', 'status', 'file_date']

with open("cases.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for case in db.cases.find().sort("_id", pymongo.ASCENDING):
        del case['metadata']
        case['id'] = case.pop('_id')
        writer.writerow(case)
