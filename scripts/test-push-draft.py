#!/usr/bin/env python3
import requests
import sys
import os
import json
import urllib3
urllib3.disable_warnings()

def load_env(path):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

load_env('/vol2/1000/docker_related/gzh-worker/.env')

WORKER_SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')

with open('/tmp/summary.txt', 'r', encoding='utf-8') as f:
    summary = f.read()

payload = {
    "title": "今日财经观察｜2026-05-26",
    "summary": summary,
    "source": {
        "bvid": "BV1BjVEzRE8N",
        "url": "https://www.bilibili.com/video/BV1BjVEzRE8N",
        "up_uid": 290663424,
        "up_name": "",
        "published_at": "2026-05-26"
    }
}

print("=== 推送到公众号草稿 ===")
print(f"Worker Secret: {WORKER_SECRET[:8]}...")
print(f"标题: {payload['title']}")
print(f"总结长度: {len(summary)} 字符")

headers = {
    "Content-Type": "application/json",
    "X-Worker-Secret": WORKER_SECRET
}

resp = requests.post(
    'http://8.134.248.11:39800/api/bilibili/summary',
    json=payload,
    headers=headers,
    timeout=60
)

print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")

if resp.status_code == 200:
    result = resp.json()
    if result.get('success'):
        print(f"\n✅ 推送成功！草稿 media_id: {result.get('media_id')}")
    else:
        print(f"\n❌ 推送失败: {result.get('message')}")
else:
    print(f"\n❌ HTTP错误: {resp.status_code}")
