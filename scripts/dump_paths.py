import json
import sys
d = json.load(sys.stdin)
for p in d["paths"]:
    print(p)
