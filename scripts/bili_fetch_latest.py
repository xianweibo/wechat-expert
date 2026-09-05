#!/usr/bin/env python3
"""Fetch latest charged video from BiliBili UP master via dynamic API."""
import json
import urllib.request
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
BILI_JCT = 'de6ed23d674a50a73865adae67069017'
UP_UID = 290663424


def get(url, referer=None):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Cookie', f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}')
    if referer:
        req.add_header('Referer', referer)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


print('=== 1. 动态 API: /x/polymer/web-dynamic/v1/feed/space ===', flush=True)
try:
    r = get(f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={UP_UID}',
            referer=f'https://space.bilibili.com/{UP_UID}/dynamic')
    if r.get('code') != 0:
        print(f'  Failed: {r.get("message")}', flush=True)
    else:
        items = r.get('data', {}).get('items', [])
        print(f'  Got {len(items)} dynamic items', flush=True)
        # 提取所有动态中的视频 bvid
        bvids = []
        for it in items[:20]:
            archive = it.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('archive', {})
            if not archive:
                # 尝试其他字段
                archive = it.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('live', {})
            bvid = archive.get('bvid')
            title = archive.get('title', '')
            if bvid:
                pub_ts = it.get('modules', {}).get('module_author', {}).get('pub_ts', 0)
                bvids.append((bvid, title, pub_ts))
                pub_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(pub_ts)) if pub_ts else 'N/A'
                print(f'    {bvid} | {pub_str} | {title[:50]}', flush=True)
        print(f'  Total bvid: {len(bvids)}', flush=True)
except Exception as e:
    print(f'  EXC: {e}', flush=True)

print('\n=== 2. 空间 API: /x/space/wbi/arc/search (WBI 签名) ===', flush=True)
try:
    r = get(f'https://api.bilibili.com/x/space/wbi/arc/search?mid={UP_UID}&ps=15&pn=1&order=pubdate',
            referer=f'https://space.bilibili.com/{UP_UID}/')
    if r.get('code') != 0:
        print(f'  Failed: {r.get("message")}', flush=True)
    else:
        vlist = r.get('data', {}).get('list', {}).get('vlist', [])
        print(f'  Got {len(vlist)} videos', flush=True)
        for v in vlist[:10]:
            pub_str = time.strftime('%Y-%m-%d', time.localtime(v.get('created', 0)))
            print(f'    {v.get("bvid")} | {pub_str} | {v.get("title", "")[:50]}', flush=True)
except Exception as e:
    print(f'  EXC: {e}', flush=True)

print('\n=== 3. 老空间 API: /x/space/arc/search ===', flush=True)
try:
    r = get(f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps=15&pn=1&order=pubdate',
            referer=f'https://space.bilibili.com/{UP_UID}/')
    if r.get('code') != 0:
        print(f'  Failed: {r.get("message")}', flush=True)
    else:
        vlist = r.get('data', {}).get('list', {}).get('vlist', [])
        print(f'  Got {len(vlist)} videos', flush=True)
        for v in vlist[:10]:
            pub_str = time.strftime('%Y-%m-%d', time.localtime(v.get('created', 0)))
            print(f'    {v.get("bvid")} | {pub_str} | {v.get("title", "")[:50]}', flush=True)
except Exception as e:
    print(f'  EXC: {e}', flush=True)
