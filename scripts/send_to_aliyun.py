import requests
import json
import sys

with open("/tmp/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()

ALIYUN_API = "https://gzh.relexplace.com/api/bilibili/summary"
WORKER_SECRET = "gzh_worker_secret_2026"

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
print(f"URL: {ALIYUN_API}")

headers = {
    "Content-Type": "application/json",
    "X-Worker-Secret": WORKER_SECRET
}

resp = requests.post(ALIYUN_API, json=payload, headers=headers, timeout=60, verify=False)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

if resp.status_code == 200:
    result = resp.json()
    if result.get("success"):
        print(f"\n✅ 成功！草稿 media_id: {result.get('media_id')}")
    else:
        print(f"\n❌ 失败: {result.get('message')}")
        sys.exit(1)
else:
    print(f"\n❌ HTTP错误: {resp.status_code}")
    sys.exit(1)