import os
import json
import urllib.request

API_KEY = "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo"

# Try a few common base URLs and model names
bases = [
    "https://api.minimaxi.com/v1/embeddings",
    "https://api.minimax.chat/v1/embeddings",
    "https://api.minimaxi.com/v1/embedding/create",
    "https://api.minimax.chat/v1/embedding/create",
]
models = ["embo-01", "text-embedding-001", "MiniMax-Text-01", "minimax-embedding"]

text = "测试"

for base in bases:
    for m in models:
        body = json.dumps({"model": m, "input": text}).encode("utf-8")
        req = urllib.request.Request(
            base, data=body,
            headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                resp = r.read().decode("utf-8")
                d = json.loads(resp)
                print("OK", base, m, "->", str(d)[:300])
                break
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, base, m, "->", e.read().decode("utf-8", errors="replace")[:200])
        except Exception as e:
            print("ERR", base, m, "->", str(e)[:100])
