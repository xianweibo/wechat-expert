import os
import json
import urllib.request

API_KEY = os.environ.get('MINIMAX_API_KEY', '')

# MiniMax API uses "texts" param
body = json.dumps({
    "model": "embo-01",
    "texts": ["测试", "中欧贸易摩擦烈度上升"],
    "type": "db",
}).encode("utf-8")
req = urllib.request.Request(
    "https://api.minimaxi.com/v1/embeddings",
    data=body,
    headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    resp = r.read().decode("utf-8")
    d = json.loads(resp)
    if d.get("vectors"):
        print("OK, got", len(d["vectors"]), "vectors, first dim:", len(d["vectors"][0]))
        print("first 5:", d["vectors"][0][:5])
        print("usage:", d.get("usage"))
    else:
        print("response:", str(d)[:500])
