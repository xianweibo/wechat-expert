#!/usr/bin/env python3
import requests
import sys
import os
import glob
import subprocess
from datetime import datetime

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

SESSDATA = os.environ.get('BILIBILI_SESSDATA', '')
BILI_JCT = os.environ.get('BILIBILI_BILI_JCT', '')
MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY', '')
WORKER_SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')

UP_UID = 290663424

cookies = {'SESSDATA': SESSDATA, 'bili_jct': BILI_JCT}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}

print("=== Step 1: 获取UP主最新充电视频 ===")

def get_video_list(page=1, page_size=30):
    resp = requests.get(
        f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps={page_size}&pn={page}&order=pubdate',
        cookies=cookies, headers=headers, timeout=30
    )
    data = resp.json()
    vlist = data.get('data', {}).get('list', {}).get('vlist', [])
    if not vlist:
        resp2 = requests.get(
            f'https://api.bilibili.com/x/space/wbi/arc/search?mid={UP_UID}&ps={page_size}&pn={page}',
            cookies=cookies, headers=headers, timeout=30
        )
        data2 = resp2.json()
        vlist = data2.get('data', {}).get('list', {}).get('vlist', [])
    return vlist

def is_charged_video(bvid):
    resp = requests.get(
        f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
        cookies=cookies, headers=headers, timeout=15
    )
    data = resp.json()
    rights = data.get('data', {}).get('rights', {})
    ugc_pay = rights.get('ugc_pay', 0)
    return ugc_pay == 1

bvid = None
title = None
pubdate = None

vlist = get_video_list(page=1, page_size=30)
if not vlist:
    print("获取视频列表失败，尝试直接用已知BV号...")
    bvid = 'BV1BjVEzRE8N'
    title = '手动指定'
else:
    print(f"获取到 {len(vlist)} 个视频，开始筛选充电视频...")
    for i, v in enumerate(vlist):
        bv = v['bvid']
        vt = v['title']
        print(f"  检查 [{i+1}/{len(vlist)}] {bv} - {vt}", end="")
        try:
            if is_charged_video(bv):
                print(" ✅ 充电视频")
                bvid = bv
                title = vt
                pubdate = datetime.fromtimestamp(v.get('created', 0)).strftime('%Y-%m-%d')
                break
            else:
                print(" ❌ 非充电")
        except Exception as e:
            print(f" 检查失败: {e}")

    if not bvid:
        print("未找到充电视频，使用最新视频作为后备")
        latest = vlist[0]
        bvid = latest['bvid']
        title = latest['title']
        pubdate = datetime.fromtimestamp(latest.get('created', 0)).strftime('%Y-%m-%d')

if not pubdate:
    pubdate = datetime.now().strftime('%Y-%m-%d')

print(f"目标视频: {bvid} - {title} ({pubdate})")

print("\n=== Step 2: 下载字幕 ===")
YUTTO_AUTH = f"SESSDATA={SESSDATA};bili_jct={BILI_JCT}"
result = subprocess.run(
    ['sudo', 'docker', 'run', '--rm', '-v', '/tmp:/data', 'siguremo/yutto',
     '--auth', YUTTO_AUTH, '--subtitle-only',
     f'https://www.bilibili.com/video/{bvid}', '-d', '/data', '-b'],
    capture_output=True, text=True, timeout=120
)
print("yutto stdout:", result.stdout[-500:] if result.stdout else "")
print("yutto stderr:", result.stderr[-500:] if result.stderr else "")

srt_files = glob.glob('/tmp/**/*.srt', recursive=True)
if not srt_files:
    print("未找到字幕文件，尝试查找...")
    for root, dirs, files in os.walk('/tmp'):
        for f in files:
            if f.endswith('.srt'):
                srt_files.append(os.path.join(root, f))
    if not srt_files:
        print("确实没有字幕文件，退出")
        sys.exit(1)

print(f"找到字幕: {srt_files[0]}")

content = ""
with open(srt_files[0], 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or '-->' in line or line.isdigit():
            continue
        content += line + "\n"

print(f"字幕内容长度: {len(content)} 字符")
with open('/tmp/subtitle-clean.txt', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n=== Step 3: MiniMax AI 总结 ===")
prompt = f"""请根据以下B站视频字幕，生成适合公众号发布的精华总结。

要求：
1. 提取核心要点，分5-8个要点详细展开
2. 用通俗易懂的语言，不复述原话，用自己的语言重构
3. 保持中立，不预测涨跌
4. 篇幅控制在1000字左右，内容要充实有深度
5. 适合财经/新闻类公众号读者
6. 每个要点要有充分的论述和分析，不要只是简单罗列

字幕内容：
{content}

请直接输出总结内容，不要有前缀说明。"""

api_resp = requests.post(
    'https://api.minimaxi.com/anthropic/v1/messages',
    headers={
        'x-api-key': MINIMAX_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
    },
    json={
        'model': 'MiniMax-M2.7',
        'max_tokens': 2048,
        'messages': [{'role': 'user', 'content': prompt}]
    },
    timeout=120
)

if api_resp.status_code != 200:
    print(f"MiniMax 调用失败: {api_resp.status_code} {api_resp.text}")
    sys.exit(1)

summary = ""
for item in api_resp.json().get('content', []):
    if item.get('type') == 'text':
        summary = item.get('text', '')
        break

print(f"AI 总结 ({len(summary)} 字):\n{summary}")
with open('/tmp/summary.txt', 'w', encoding='utf-8') as f:
    f.write(summary)

print("\n=== Step 4: 推送到公众号草稿 ===")

push_resp = requests.post(
    'http://8.134.248.11:39800/api/bilibili/summary',
    headers={
        'Content-Type': 'application/json',
        'X-Worker-Secret': WORKER_SECRET
    },
    json={
        'title': title,
        'summary': summary,
        'source': {
            'bvid': bvid,
            'url': f'https://www.bilibili.com/video/{bvid}',
            'up_uid': UP_UID,
            'up_name': '',
            'published_at': pubdate
        }
    },
    timeout=60,
    verify=False
)

print(f"推送状态: {push_resp.status_code}")
print(f"推送结果: {push_resp.text}")

if push_resp.status_code == 200:
    result = push_resp.json()
    if result.get('success'):
        print(f"\n✅ 回归测试成功！草稿 media_id: {result.get('media_id')}")
    else:
        print(f"\n❌ 推送失败: {result.get('message')}")
        sys.exit(1)
else:
    print(f"\n❌ HTTP错误: {push_resp.status_code}")
    sys.exit(1)
