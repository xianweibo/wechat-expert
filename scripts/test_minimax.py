import requests
import json
import os

API_KEY = os.environ.get("MINIMAX_API_KEY", "")

if not API_KEY:
    print("错误: 环境变量 MINIMAX_API_KEY 未设置")
    exit(1)

url = "https://api.minimaxi.com/anthropic/v1/messages"

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

data = {
    "model": "MiniMax-M2.7",
    "max_tokens": 20,
    "messages": [
        {"role": "user", "content": "Hello, please respond with a short greeting."}
    ]
}

print("Testing MiniMax API...")
print(f"URL: {url}")
print(f"Headers: {headers}")
print(f"Data: {json.dumps(data)}")

try:
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
