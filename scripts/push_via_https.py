#!/usr/bin/env python3
"""Push summary to Aliyun via HTTPS endpoint."""
import requests
import json
import sys

# Read summary from file or generate
if len(sys.argv) >= 2:
    summary_file = sys.argv[1]
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = f.read()
else:
    print("Usage: python3 push_via_https.py <summary_file>")
    sys.exit(1)

ALIYUN_URL = 'https://gzh.relexplace.com/api/bilibili/summary'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'

payload = {
    "title": "《第六百九一期》中欧贸易摩擦烈度上升，是否会影响中国产业出口？欧洲的未来在何方？",
    "summary": summary,
    "source": {
        "bvid": "BV1gZ7Z6hEaP",
        "url": "https://www.bilibili.com/video/BV1gZ7Z6hEaP",
        "up_uid": 290663424,
        "up_name": "有何高见9527",
        "published_at": "2026-06-03"
    }
}

try:
    r = requests.post(
        ALIYUN_URL,
        json=payload,
        headers={
            'Content-Type': 'application/json',
            'X-Worker-Secret': WORKER_SECRET
        },
        timeout=30,
        verify=False
    )
    print(f"HTTP {r.status_code}: {r.text[:500]}")
    result = r.json()
    if result.get('success'):
        print("SUCCESS!")
    else:
        print(f"FAILED: {result.get('message', 'unknown')}")
except Exception as e:
    print(f"Exception: {e}")
