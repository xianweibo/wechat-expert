import json
import pprint
d = json.load(open("/tmp/openapi.json"))
p = pprint.PrettyPrinter(width=200)
p.pprint(d["components"]["schemas"]["AddCollectionRecordsPayload"])
print("===")
p.pprint(d["components"]["schemas"].get("AddCollectionRecordsResponse", {}))
