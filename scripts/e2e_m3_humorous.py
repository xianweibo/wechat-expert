#!/usr/bin/env python3
"""E2E push for new charged video with humorous style + MiniMax-M3."""
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

SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
BILI_JCT = 'de6ed23d674a50a73865adae67069017'
MINIMAX_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'
BVID = 'BV1wmES6FE7M'
ALIYUN = '8.134.248.11'
ALIYUN_USER = 'gongzhonghao'
SSH_KEY = r'C:\Users\Administrator\.ssh\id_ed25519'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'


def curl_get(url, extra_headers=None):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Cookie', f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}')
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


def call_minimax_m3(title, content):
    """Humorous personal style, ~1000 chars, no quotes/citations."""
    import http.client
    system_prompt = (
        '你是一个幽默风趣的公众号博主，粉丝爱看你的文章是因为你说话又皮又接地气。'
        '你的风格是脱口秀式聊天，善用夸张、反转、网络梗和自嘲，把严肃话题说得让人想笑。'
    )
    user_prompt = (
        f'请根据以下B站视频信息，写一篇拟人化、幽默滑稽风格的公众号文章。\n\n'
        f'【硬性要求】\n'
        f'1. 字数 1000 字左右（不少于 900 字，不超过 1200 字）\n'
        f'2. 风格必须幽默滑稽、像跟朋友聊天一样接地气，善用网络梗、夸张、自嘲\n'
        f'3. 绝对不能用引用块（不要 > 符号、不要"参考""引用""出处""原文""来源"等词）\n'
        f'4. 段落用 1. 2. 3. 编号或者直接分段，禁止引用格式\n'
        f'5. 标题自己起一个吸引眼球的（不要叫"总结"），可以用反问、夸张、对比\n'
        f'6. 开头可以吐槽"今天看到一个视频笑得我......"这类口语化引入\n'
        f'7. 不要在文章里写"以下""如上"这种书面语\n'
        f'8. 直接输出文章正文，不要"好的，根据您的要求"之类的前缀\n\n'
        f'【视频标题】{title}\n\n'
        f'【视频内容】\n{content[:6000]}'
    )
    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 4096,
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': user_prompt}],
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
    pubdate = d['pubdate']
    author = d['owner']['name']
    mid = d['owner']['mid']
    print(f'  Title: {title}', flush=True)
    print(f'  Author: {author} (mid={mid})', flush=True)
    print(f'  Pubdate: {time.strftime("%Y-%m-%d", time.localtime(pubdate))}', flush=True)
    print(f'  Desc length: {len(desc)}', flush=True)

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

    print('\n=== 3. MiniMax-M3 (humorous style) ===', flush=True)
    summary = call_minimax_m3(title, sub_text)
    print(f'  Summary length: {len(summary)}', flush=True)
    print(f'  --- Preview ---', flush=True)
    print(summary[:500], flush=True)
    print(f'  --- END ---', flush=True)

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

    local_payload = r'C:\Users\Docker\AppData\Local\Temp\gzh_payload_m3.json'
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
