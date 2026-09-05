#!/usr/bin/env python3
"""Retry fetch latest BiliBili videos with longer backoff."""
import json
import time
import urllib.request
import ssl
import sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
BILI_JCT = 'de6ed23d674a50a73865adae67069017'
UP_UID = 290663424


def get(url, referer=None, retries=3):
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            req.add_header('Cookie', f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}')
            if referer:
                req.add_header('Referer', referer)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            last_err = e
            wait = 10 * (i + 1)
            print(f'  Retry {i+1}/{retries} failed: {e}, wait {wait}s', flush=True)
            time.sleep(wait)
    raise last_err


# Try 1: Space arc search
print('=== Trying space arc search ===', flush=True)
try:
    r = get(f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps=15&pn=1&order=pubdate',
            referer=f'https://space.bilibili.com/{UP_UID}/')
    print(f'  code: {r.get("code")}, msg: {r.get("message")}', flush=True)
    if r.get('code') == 0:
        vlist = r['data']['list']['vlist']
        print(f'  Got {len(vlist)} videos:', flush=True)
        for v in vlist[:5]:
            pub_str = time.strftime('%Y-%m-%d', time.localtime(v.get('created', 0)))
            print(f'    {v.get("bvid")} | {pub_str} | {v.get("title", "")[:50]}', flush=True)
        sys.exit(0)
except Exception as e:
    print(f'  EXC: {e}', flush=True)

# Try 2: Dynamic API
print('\n=== Trying dynamic API ===', flush=True)
time.sleep(5)
try:
    r = get(f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={UP_UID}',
            referer=f'https://space.bilibili.com/{UP_UID}/dynamic')
    print(f'  code: {r.get("code")}, msg: {r.get("message")}', flush=True)
    if r.get('code') == 0:
        items = r.get('data', {}).get('items', [])
        print(f'  Got {len(items)} items', flush=True)
        for it in items[:5]:
            archive = it.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('archive', {})
            bvid = archive.get('bvid')
            title = archive.get('title', '')
            pub_ts = it.get('modules', {}).get('module_author', {}).get('pub_ts', 0)
            pub_str = time.strftime('%Y-%m-%d', time.localtime(pub_ts)) if pub_ts else 'N/A'
            if bvid:
                print(f'    {bvid} | {pub_str} | {title[:50]}', flush=True)
        sys.exit(0)
except Exception as e:
    print(f'  EXC: {e}', flush=True)

# Try 3: WBI signed API (newer)
print('\n=== Trying WBI arc search ===', flush=True)
time.sleep(5)
try:
    r = get(f'https://api.bilibili.com/x/space/wbi/arc/search?mid={UP_UID}&ps=15&pn=1&order=pubdate',
            referer=f'https://space.bilibili.com/{UP_UID}/')
    print(f'  code: {r.get("code")}, msg: {r.get("message")}', flush=True)
    if r.get('code') == 0:
        vlist = r.get('data', {}).get('list', {}).get('vlist', [])
        print(f'  Got {len(vlist)} videos:', flush=True)
        for v in vlist[:5]:
            pub_str = time.strftime('%Y-%m-%d', time.localtime(v.get('created', 0)))
            print(f'    {v.get("bvid")} | {pub_str} | {v.get("title", "")[:50]}', flush=True)
        sys.exit(0)
except Exception as e:
    print(f'  EXC: {e}', flush=True)

print('\nAll APIs still rate-limited. B站 风控 not cooled down.', flush=True)
