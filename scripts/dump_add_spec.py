import json
import sys
import pprint
d = json.load(open("/tmp/openapi.json"))
path = "/api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/add"
p = pprint.PrettyPrinter(width=200)
p.pprint(d["paths"][path])
