#!/usr/bin/env python3
import requests
import json

url = "http://127.0.0.1:39800/api/bilibili/summary"
headers = {
    "Content-Type": "application/json",
    "X-Worker-Secret": "cBsFHdghYA1W07VpultIKEynOSQwNM8z"
}
payload = {
    "title": "test",
    "summary": "hello",
    "source": {
        "bvid": "BV1test",
        "url": "https://test.com",
        "up_uid": 1,
        "up_name": "test",
        "published_at": "2026-05-26"
    }
}

r = requests.post(url, json=payload, headers=headers, timeout=30)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
