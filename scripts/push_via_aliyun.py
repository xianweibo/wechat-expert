#!/usr/bin/env python3
"""Generate summary and push via SSH jump to Aliyun."""
import requests
import json
import sys

if len(sys.argv) >= 5:
    title = sys.argv[1]
    description = sys.argv[2]
    bvid = sys.argv[3]
    pubdate = int(sys.argv[4])
else:
    print("Usage: python3 push_via_aliyun.py <title> <description> <bvid> <pubdate>")
    sys.exit(1)

MINIMAX_API_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'
ALIYUN_API_URL = 'http://127.0.0.1:39800/api/bilibili/summary'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'

from datetime import datetime
published_at = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d') if pubdate else datetime.now().strftime('%Y-%m-%d')

# Step 1: Generate summary via MiniMax
print(f"[Step 1/2] Generating summary for: {title}")
print(f"  BVID: {bvid}")

prompt = f"""你是一个财经学习内容整理助手。请根据以下视频简介，生成一段精华总结。

视频标题：{title}
视频简介：{description}
字幕内容：（无字幕）

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

# Step 2: Push to Aliyun API (via SSH tunnel inside this script)
print(f"\n[Step 2/2] Pushing to WeChat draft via SSH jump to Aliyun...")

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

# Save payload to file
import os
payload_file = '/tmp/wechat_payload.json'
with open(payload_file, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"  Payload saved to {payload_file}")
print(f"  Please run SSH command to push:")
print(f"  ssh -i /tmp/id_ed25519 -p 39022 user@8.134.248.11 'curl -X POST http://127.0.0.1:39800/api/bilibili/summary -H \"Content-Type: application/json\" -H \"X-Worker-Secret: {WORKER_SECRET}\" -d @{payload_file}'")
