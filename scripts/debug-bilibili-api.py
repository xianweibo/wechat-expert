import os
#!/usr/bin/env python3
import subprocess, os, json, re, time

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
YUTTO_AUTH = f"SESSDATA={SESSDATA};bili_jct={BILI_JCT}" if SESSDATA and BILI_JCT else ""

UP_UID = 290663424

print("=== Using yutto to list videos ===")
result = subprocess.run(
    ['sudo', 'docker', 'run', '--rm', 'siguremo/yutto',
     '--auth', YUTTO_AUTH,
     '--subtitle-only',
     f'https://space.bilibili.com/{UP_UID}',
     '-d', '/data',
     '-b',
     '--no-progress'],
    capture_output=True, text=True, timeout=120
)
print("STDOUT:", result.stdout[-2000:] if result.stdout else "")
print("STDERR:", result.stderr[-1000:] if result.stderr else "")

import requests
cookies = {'SESSDATA': SESSDATA, 'bili_jct': BILI_JCT}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Referer': 'https://www.bilibili.com/'}

print("\n=== Wait 5s then try API again ===")
time.sleep(5)
resp = requests.get(
    f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps=5&pn=1&order=pubdate',
    cookies=cookies, headers=headers, timeout=30
)
print(f'Status: {resp.status_code}, Length: {len(resp.text)}')
if resp.text:
    try:
        data = resp.json()
        print(f'Code: {data.get("code")}, Message: {data.get("message")}')
        vlist = data.get('data', {}).get('list', {}).get('vlist', [])
        if vlist:
            for v in vlist[:5]:
                print(f'  {v["bvid"]} - {v["title"]}')
    except:
        print(f'Raw: {resp.text[:200]}')
