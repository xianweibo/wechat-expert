import requests
import json

url = "https://api.minimaxi.com/anthropic/v1/messages"
headers = {
    "x-api-key": "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo",
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
