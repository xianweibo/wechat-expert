import requests
import json
import sys

# Read summary
with open("/tmp/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

# Send to Alibaba Cloud
payload = {
    "title": "【B站视频精华】全球格局重塑信号密集释放",
    "summary": summary,
    "source": {
        "bvid": "BV191Lu64EWD",
        "url": "https://www.bilibili.com/video/BV191Lu64EWD",
        "up_uid": 290663424,
        "up_name": "有何高见9527",
        "published_at": "2026-05-19"
    }
}

print("发送到阿里云服务器...")
print(json.dumps(payload, ensure_ascii=False, indent=2))

resp = requests.post(
    "http://8.134.248.11:3000/api/bilibili/summary",
    json=payload,
    timeout=30
)

print(f"\nStatus: {resp.status_code}")
print(f"Response: {resp.text}")
