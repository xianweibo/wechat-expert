import requests
import json

API_KEY = "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo"

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
