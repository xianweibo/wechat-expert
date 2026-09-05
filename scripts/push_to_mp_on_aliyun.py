#!/usr/bin/env python3
"""
阿里云端推送脚本 — 调用 gzh-expert-app 容器的 /api/bilibili/summary 接口
推送由阿里云 (8.134.248.11) 发起，公众号白名单内
"""
import sys
import requests

ALIYUN_API_URL = 'http://127.0.0.1:39800/api/bilibili/summary'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'


def push(title: str, content: str, bvid: str, aid: str) -> dict:
    payload = {
        'title': title,
        'content': content,
        'bvid': bvid,
        'aid': aid,
        'coverB64': '',
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Worker-Secret': WORKER_SECRET,
    }
    r = requests.post(ALIYUN_API_URL, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print('用法: push_to_mp_on_aliyun.py <title> <content> <bvid> <aid>')
        sys.exit(2)
    title = sys.argv[1]
    content = sys.argv[2]
    bvid = sys.argv[3]
    aid = sys.argv[4]
    result = push(title, content, bvid, aid)
    print('=== 推送结果 ===')
    print(result)
    if result.get('success'):
        print('✅ 推送成功')
        sys.exit(0)
    else:
        print('❌ 推送失败')
        sys.exit(1)
