#!/usr/bin/env python3
"""NAS-side: receive video info from sandbox, call MiniMax, push to draft."""
import requests
import json
import sys
import os

# Read video info from stdin or env
if len(sys.argv) >= 5:
    title = sys.argv[1]
    description = sys.argv[2]
    bvid = sys.argv[3]
    pubdate = int(sys.argv[4])
else:
    print("Usage: python3 summary_and_push.py <title> <description> <bvid> <pubdate>")
    sys.exit(1)

MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
# Use Aliyun API via frpc tunnel (NAS 39800 -> Aliyun 8.134.248.11:39802)
ALIYUN_API_URL = 'http://8.134.248.11:39802/api/bilibili/summary'
WORKER_SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')

# Disable worker auth (gzh-expert-app container doesn't have BILIBILI_WORKER_SECRET set)
USE_AUTH = True

print(f"[Step 1/2] Generating summary for: {title}")
print(f"  BVID: {bvid}")
print(f"  Description length: {len(description)} chars")

prompt = f"""你是一个财经学习内容整理助手。请根据以下视频简介，生成一段精华总结。

视频标题：{title}
视频简介：{description}
字幕内容：
（无字幕）

要求：
- 提取核心要点，分5-8个要点详细展开
- 用通俗易懂的语言
- 不复述原话，用自己语言重构
- 保持中立，不预测涨跌
- 篇幅控制在1000字左右，内容要充实有深度
- 每个要点要有充分的论述和分析，不要只是简单罗列"""

url = "https://api.minimaxi.com/anthropic/v1/messages"
headers = {
    "x-api-key": MINIMAX_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}
data = {
    "model": "MiniMax-M2.7",
    "max_tokens": 2048,
    "messages": [{"role": "user", "content": prompt}]
}

try:
    r = requests.post(url, headers=headers, json=data, timeout=120)
    if r.status_code == 200:
        result = r.json()
        summary = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                summary = item.get("text", "")
                break
        if not summary:
            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"  Summary generated: {len(summary)} chars")
        print(f"  Preview: {summary[:200]}...")
    else:
        print(f"  MiniMax error: {r.status_code} - {r.text[:300]}")
        sys.exit(1)
except Exception as e:
    print(f"  Exception: {e}")
    sys.exit(1)

print(f"\n[Step 2/2] Pushing to WeChat draft...")

from datetime import datetime
published_at = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d') if pubdate else datetime.now().strftime('%Y-%m-%d')

payload = {
    "title": title,
    "summary": summary,
    "source": {
        "bvid": bvid,
        "url": f"https://www.bilibili.com/video/{bvid}",
        "up_uid": 290663424,
        "up_name": "有何高见9527",
        "published_at": published_at
    }
}

try:
    headers = {'Content-Type': 'application/json'}
    if USE_AUTH:
        headers['X-Worker-Secret'] = WORKER_SECRET
    r = requests.post(
        ALIYUN_API_URL,
        json=payload,
        headers=headers,
        timeout=30
    )
    print(f"  Response: {r.status_code} - {r.text[:300]}")
    result = r.json()
    if result.get('success'):
        print("\n  SUCCESS: Summary pushed to WeChat draft!")
        sys.exit(0)
    else:
        print(f"\n  FAILED: {result.get('message', 'unknown error')}")
        sys.exit(1)
except Exception as e:
    print(f"  Exception: {e}")
    sys.exit(1)
