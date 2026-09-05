#!/bin/bash
curl -s "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid=290663424" \
  -H "Referer: https://www.bilibili.com" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('data', {}).get('items', [])
print(f'Total items: {len(items)}')
for item in items:
    major = item.get('modules', {}).get('module_dynamic', {}).get('major', {})
    archive = major.get('archive', {})
    bvid = archive.get('bvid', '')
    title = archive.get('title', '')
    if bvid:
        print(f'  {bvid} - {title}')
"
