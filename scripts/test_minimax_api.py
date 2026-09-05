import os
import requests
import json

url = "https://api.minimaxi.com/anthropic/v1/messages"
headers = {
    "x-api-key": os.environ.get('MINIMAX_API_KEY', ''),
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}
data = {
    "model": "MiniMax-M2.7",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": "hello, respond with just 'ok'"}]
}

try:
    r = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
