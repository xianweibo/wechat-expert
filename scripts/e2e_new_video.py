#!/usr/bin/env python3
"""E2E push for new charged video BV1wmES6FE7M."""
import json
import time
import subprocess
import urllib.request
import ssl
import sys
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SESSDATA = os.environ.get('BILIBILI_SESSDATA', '')
BILI_JCT = os.environ.get('BILIBILI_BILI_JCT', '')
MINIMAX_KEY = os.environ.get('MINIMAX_API_KEY', '')
BVID = 'BV1wmES6FE7M'
ALIYUN = '8.134.248.11'
ALIYUN_USER = 'gongzhonghao'
SSH_KEY = r'C:\Users\Administrator\.ssh\id_ed25519'
WORKER_SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')


def curl_get(url, extra_headers=None):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Cookie', f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}')
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


def call_minimax(title, content):
    import http.client
    prompt = (
        f'请根据以下B站视频信息生成中文总结（600-800字）：\n\n'
        f'【标题】{title}\n\n'
        f'【内容】\n{content[:6000]}'
    )
    body = json.dumps({
        'model': 'MiniMax-M2.7',
        'max_tokens': 2048,
        'messages': [{'role': 'user', 'content': prompt}],
    }, ensure_ascii=False).encode('utf-8')
    conn = http.client.HTTPSConnection('api.minimaxi.com', timeout=120)
    conn.request(
        'POST',
        '/anthropic/v1/messages',
        body=body,
        headers={
            'x-api-key': MINIMAX_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json; charset=utf-8',
        },
    )
    resp = conn.getresponse()
    data = json.loads(resp.read().decode('utf-8'))
    if data.get('error'):
        raise RuntimeError(f'MiniMax error: {data["error"]}')
    for item in data.get('content', []):
        if item.get('type') == 'text':
            return item['text']
    raise RuntimeError('MiniMax returned no text')


def main():
    print('=== 1. BiliBili video detail ===', flush=True)
    detail = curl_get(f'https://api.bilibili.com/x/web-interface/view?bvid={BVID}',
                      {'Referer': f'https://www.bilibili.com/video/{BVID}'})
    if detail['code'] != 0:
        raise RuntimeError(f'BiliBili: {detail["message"]}')
    d = detail['data']
    title = d['title']
    desc = d['desc']
    pic = d['pic']
    pubdate = d['pubdate']
    author = d['owner']['name']
    mid = d['owner']['mid']
    print(f'  Title: {title}', flush=True)
    print(f'  Author: {author} (mid={mid})', flush=True)
    print(f'  Pubdate: {time.strftime("%Y-%m-%d", time.localtime(pubdate))}', flush=True)
    print(f'  Desc length: {len(desc)}', flush=True)

    # Check charged
    rights = d.get('rights', {})
    is_charged = (rights.get('is_charging_arc') == 1
                  or rights.get('ugc_pay') == 1
                  or d.get('is_upower_exclusive') is True
                  or d.get('is_upower_play') is True)
    print(f'  Is charged: {is_charged}', flush=True)
    if not is_charged:
        print('  WARNING: Not detected as charged video, continuing anyway', flush=True)

    print('\n=== 2. Try subtitle, fallback to desc ===', flush=True)
    cid = d['pages'][0]['cid']
    sub_text = ''
    try:
        player = curl_get(f'https://api.bilibili.com/x/player/v2?bvid={BVID}&cid={cid}')
        subs = player['data']['subtitle']['subtitles']
        if subs:
            sub_url = 'https:' + subs[0]['subtitle_url']
            print(f'  Subtitle URL: {sub_url}', flush=True)
            sub_data = curl_get(sub_url)
            sub_text = '\n'.join(item.get('content', '') for item in sub_data.get('body', []))
            print(f'  Subtitle length: {len(sub_text)}', flush=True)
    except Exception as e:
        print(f'  Subtitle error: {e}', flush=True)
    if not sub_text:
        sub_text = desc
        if d.get('dynamic'):
            sub_text += '\n' + d['dynamic']
        print(f'  Fallback to desc, length: {len(sub_text)}', flush=True)

    print('\n=== 3. MiniMax ===', flush=True)
    summary = call_minimax(title, sub_text)
    print(f'  Summary length: {len(summary)}', flush=True)
    print(f'  Preview: {summary[:200]}', flush=True)

    print('\n=== 4. Push to Aliyun gzh-expert-app via SSH ===', flush=True)
    payload = {
        'title': title,
        'summary': summary,
        'source': {
            'bvid': BVID,
            'url': f'https://www.bilibili.com/video/{BVID}',
            'up_uid': int(mid),
            'up_name': author,
            'published_at': time.strftime('%Y-%m-%d', time.localtime(pubdate)),
        },
    }

    local_payload = r'C:\Users\Docker\AppData\Local\Temp\gzh_payload_new.json'
    with open(local_payload, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)

    print('  scp...', flush=True)
    scp = subprocess.run(
        ['scp', '-P', '22', '-i', SSH_KEY,
         '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL',
         '-o', 'BatchMode=yes',
         local_payload, f'{ALIYUN_USER}@{ALIYUN}:/tmp/gzh_payload.json'],
        capture_output=True, text=True
    )
    if scp.returncode != 0:
        raise RuntimeError(f'scp failed: {scp.stderr}')

    print('  ssh + curl POST...', flush=True)
    ssh = subprocess.run(
        ['ssh', '-p', '22', '-i', SSH_KEY,
         '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=NUL',
         '-o', 'BatchMode=yes',
         f'{ALIYUN_USER}@{ALIYUN}',
         f"curl -sS -X POST -H 'Content-Type: application/json' "
         f"-H 'X-Worker-Secret: {WORKER_SECRET}' "
         f"--data-binary @/tmp/gzh_payload.json "
         f"http://127.0.0.1:39800/api/bilibili/summary"],
        capture_output=True, text=True
    )
    print(f'  ssh stdout: {ssh.stdout}', flush=True)
    print(f'  ssh stderr: {ssh.stderr}', flush=True)

    print('\n=== Done ===', flush=True)
    print(f'Result: {ssh.stdout}', flush=True)


if __name__ == '__main__':
    main()
