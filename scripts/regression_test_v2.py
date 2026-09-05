#!/usr/bin/env python3
"""Regression test: fetch latest charged video, generate summary, push to WeChat draft."""
import requests
import json
import sys
import time

# Config
UP_UID = 290663424
SESSDATA = '9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC'
BILI_JCT = 'de6ed23d674a50a73865adae67069017'
MINIMAX_API_KEY = 'sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo'
ALIYUN_API_URL = 'http://8.134.248.11:3000/api/bilibili/summary'
WORKER_SECRET = 'cBsFHdghYA1W07VpultIKEynOSQwNM8z'

cookies = {'SESSDATA': SESSDATA, 'bili_jct': BILI_JCT}
req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}

def step1_get_latest_charged_video():
    """Step 1: Get latest charged video from dynamic API or regular API."""
    print("[1/5] Getting latest charged video...")

    # Try dynamic API first
    print("  Trying dynamic API...")
    try:
        resp = requests.get(
            f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={UP_UID}',
            cookies=cookies, headers=req_headers, timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 0:
                items = data.get('data', {}).get('item', [])
                for item in items:
                    major = item.get('modules', {}).get('module_dynamic', {}).get('major', {})
                    if major.get('type') == 'MAJOR_TYPE_ARCHIVE':
                        archive = major.get('archive', {})
                        is_charging = archive.get('is_charging_arc', False)
                        badge = archive.get('badge', {}).get('text', '')
                        if is_charging or '充电' in badge:
                            video = {
                                'bvid': archive.get('aid', ''),  # might be aid
                                'title': archive.get('title', ''),
                                'pubdate': item.get('modules', {}).get('module_author', {}).get('pub_ts', 0),
                                'is_charging': True
                            }
                            # Get bvid from arc url
                            arc_url = archive.get('jump_url', '')
                            if 'BV' in arc_url:
                                import re
                                bv_match = re.search(r'BV\w+', arc_url)
                                if bv_match:
                                    video['bvid'] = bv_match.group()
                            else:
                                video['bvid'] = f"BV{archive.get('bvid', '')}"

                            print(f"  Found charged video from dynamic API: {video['title']} ({video['bvid']})")
                            return video
                print("  No charged video in dynamic API results")
            else:
                print(f"  Dynamic API error: code={data.get('code')}, msg={data.get('message')}")
        else:
            print(f"  Dynamic API HTTP error: {resp.status_code}")
    except Exception as e:
        print(f"  Dynamic API exception: {e}")

    # Fallback to regular API
    print("  Trying regular API...")
    try:
        resp = requests.get(
            f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps=30&pn=1&order=pubdate',
            cookies=cookies, headers=req_headers, timeout=30
        )
        data = resp.json()
        vlist = data.get('data', {}).get('list', {}).get('vlist', [])
        for v in vlist:
            if v.get('is_charging_arc', False) or v.get('elec_arc_type', 0) > 0:
                video = {
                    'bvid': v['bvid'],
                    'title': v['title'],
                    'pubdate': v.get('created', 0),
                    'is_charging': True
                }
                print(f"  Found charged video from regular API: {video['title']} ({video['bvid']})")
                return video
        # If no charged video, take the latest
        if vlist:
            v = vlist[0]
            video = {
                'bvid': v['bvid'],
                'title': v['title'],
                'pubdate': v.get('created', 0),
                'is_charging': v.get('is_charging_arc', False)
            }
            print(f"  No charged video found, using latest: {video['title']} ({video['bvid']})")
            return video
    except Exception as e:
        print(f"  Regular API exception: {e}")

    print("  ERROR: Could not get any video!")
    return None

def step2_get_video_detail(bvid):
    """Step 2: Get video detail including cid and description."""
    print(f"[2/5] Getting video detail for {bvid}...")
    try:
        resp = requests.get(
            f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
            cookies=cookies, headers=req_headers, timeout=30
        )
        data = resp.json()
        if data.get('code') == 0:
            v = data['data']
            detail = {
                'title': v['title'],
                'description': v.get('desc', ''),
                'cid': v.get('cid', 0),
                'owner_mid': v.get('owner', {}).get('mid', UP_UID),
                'owner_name': v.get('owner', {}).get('name', ''),
                'pubdate': v.get('pubdate', 0),
                'duration': v.get('duration', 0),
            }
            print(f"  Title: {detail['title']}")
            print(f"  CID: {detail['cid']}")
            print(f"  Duration: {detail['duration']}s")
            return detail
        else:
            print(f"  Error: {data.get('message')}")
    except Exception as e:
        print(f"  Exception: {e}")
    return None

def step3_get_subtitle(bvid, cid):
    """Step 3: Get subtitle text."""
    print(f"[3/5] Getting subtitle for {bvid} (cid={cid})...")
    try:
        resp = requests.get(
            f'https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}',
            cookies=cookies, headers=req_headers, timeout=30
        )
        data = resp.json()
        if data.get('code') == 0:
            subtitles = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
            if subtitles:
                sub_url = subtitles[0].get('subtitle_url', '')
                if sub_url:
                    if sub_url.startswith('//'):
                        sub_url = 'https:' + sub_url
                    print(f"  Downloading subtitle from: {sub_url[:80]}...")
                    sub_resp = requests.get(sub_url, headers=req_headers, timeout=15)
                    sub_data = sub_resp.json()
                    lines = []
                    for item in sub_data.get('body', []):
                        text = item.get('content', '').strip()
                        if text:
                            lines.append(text)
                    subtitle_text = ' '.join(lines)
                    print(f"  Subtitle length: {len(subtitle_text)} chars")
                    return subtitle_text
            print("  No subtitle available")
        else:
            print(f"  Error: {data.get('message')}")
    except Exception as e:
        print(f"  Exception: {e}")
    return ''

def step4_generate_summary(title, description, subtitle_text, bvid):
    """Step 4: Generate summary using MiniMax API."""
    print(f"[4/5] Generating summary with MiniMax...")

    prompt = f"""你是一个财经学习内容整理助手。请根据以下视频字幕和简介，生成一段精华总结。

视频标题：{title}
视频简介：{description}
字幕内容：
{subtitle_text or '（无字幕）'}

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
            return summary
        else:
            print(f"  MiniMax error: {r.status_code} - {r.text[:300]}")
    except Exception as e:
        print(f"  Exception: {e}")
    return ''

def step5_push_to_draft(title, summary, bvid, owner_mid, owner_name, pubdate):
    """Step 5: Push summary to Aliyun API (WeChat draft)."""
    print(f"[5/5] Pushing to WeChat draft...")

    from datetime import datetime
    published_at = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d') if pubdate else datetime.now().strftime('%Y-%m-%d')

    payload = {
        "title": title,
        "summary": summary,
        "source": {
            "bvid": bvid,
            "url": f"https://www.bilibili.com/video/{bvid}",
            "up_uid": owner_mid,
            "up_name": owner_name,
            "published_at": published_at
        }
    }

    try:
        r = requests.post(
            ALIYUN_API_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Worker-Secret': WORKER_SECRET
            },
            timeout=30
        )
        print(f"  Response: {r.status_code} - {r.text[:300]}")
        result = r.json()
        if result.get('success'):
            print("  SUCCESS: Summary pushed to WeChat draft!")
            return True
        else:
            print(f"  FAILED: {result.get('message', 'unknown error')}")
    except Exception as e:
        print(f"  Exception: {e}")
    return False

def main():
    print("=" * 50)
    print("Regression Test - Full Pipeline")
    print("=" * 50)

    # Step 1: Get latest charged video
    video = step1_get_latest_charged_video()
    if not video:
        print("FAILED: Could not get video list")
        sys.exit(1)

    bvid = video['bvid']
    print(f"\nTarget video: {video['title']} ({bvid})")

    # Step 2: Get video detail
    detail = step2_get_video_detail(bvid)
    if not detail:
        print("FAILED: Could not get video detail")
        sys.exit(1)

    # Step 3: Get subtitle
    subtitle_text = step3_get_subtitle(bvid, detail['cid'])

    # Step 4: Generate summary
    summary = step4_generate_summary(
        detail['title'],
        detail['description'],
        subtitle_text,
        bvid
    )
    if not summary:
        print("FAILED: Could not generate summary")
        sys.exit(1)

    # Step 5: Push to draft
    success = step5_push_to_draft(
        detail['title'],
        summary,
        bvid,
        detail['owner_mid'],
        detail['owner_name'],
        detail['pubdate']
    )

    if success:
        print("\n" + "=" * 50)
        print("REGRESSION TEST PASSED!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("REGRESSION TEST FAILED at step 5")
        print("=" * 50)
        sys.exit(1)

if __name__ == '__main__':
    main()
