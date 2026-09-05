#!/usr/bin/env python3
"""
End-to-end 推送脚本: 抓 B站最新视频 -> 生成 AI 总结 -> POST 给阿里云 gzh-expert-app
推送由阿里云 (8.134.248.11) 发起，公众号白名单内。
"""
import sys
import json
import time
import urllib.request
import urllib.error
import requests
import subprocess
import os

# === 配置 (从 NAS gzh-worker 容器读到的) ===
SESSDATA = os.environ.get('BILIBILI_SESSDATA', '')
BILI_JCT = os.environ.get('BILIBILI_BILI_JCT', '')
TARGET_UP_UID = 290663424
MINIMAX_KEY = os.environ.get('MINIMAX_API_KEY', '')
ALIYUN_API = 'http://127.0.0.1:39800/api/bilibili/summary'
WORKER_SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def get_latest_charged_video():
    """通过 B站空间 API 获取 UP 主最新视频。"""
    log(f'>>> 抓取 UP 主 {TARGET_UP_UID} 最新视频')
    url = f'https://api.bilibili.com/x/space/arc/search?mid={TARGET_UP_UID}&ps=10&pn=1'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cookie': f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}',
        'Referer': f'https://space.bilibili.com/{TARGET_UP_UID}/',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if data.get('code') != 0:
        raise RuntimeError(f'B站空间API失败: {data}')
    vlist = data['data']['list']['vlist']
    log(f'    拿到 {len(vlist)} 个视频')
    return vlist


def get_video_detail(bvid):
    log(f'>>> 抓取视频详情 {bvid}')
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cookie': f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if data.get('code') != 0:
        raise RuntimeError(f'B站视频API失败: {data}')
    return data['data']


def get_subtitle(bvid, cid):
    log(f'>>> 抓取字幕 (cid={cid})')
    url = f'https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cookie': f'SESSDATA={SESSDATA}; bili_jct={BILI_JCT}',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    if data.get('code') != 0:
        log(f'    player API code={data.get("code")}（可能没有字幕）')
        return ''
    subtitles = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
    if not subtitles:
        log('    该视频没有字幕')
        return ''
    sub_url = 'https:' + subtitles[0]['subtitle_url']
    log(f'    字幕 URL: {sub_url}')
    with urllib.request.urlopen(sub_url, timeout=20) as resp:
        sub_data = json.loads(resp.read().decode('utf-8'))
    body = sub_data.get('body', [])
    text = '\n'.join(item.get('content', '') for item in body)
    log(f'    字幕长度: {len(text)}')
    return text


def call_minimax(title, content):
    log('>>> 调用 MiniMax 生成总结')
    prompt = f'请根据以下B站视频信息生成中文总结（600-800字）：\n\n【标题】{title}\n\n【字幕】\n{content[:6000]}'
    payload = {
        'model': 'MiniMax-M2.7',
        'max_tokens': 2048,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    r = requests.post(
        'https://api.minimaxi.com/anthropic/v1/messages',
        json=payload,
        headers={
            'x-api-key': MINIMAX_KEY,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    if data.get('error'):
        raise RuntimeError(f'MiniMax错误: {data["error"]}')
    content_arr = data.get('content', [])
    summary = ''
    for item in content_arr:
        if item.get('type') == 'text':
            summary = item.get('text', '')
            break
    if not summary:
        summary = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    log(f'    总结长度: {len(summary)}')
    return summary


def push_to_aliyun(title, summary, video):
    log(f'>>> POST 到阿里云 {ALIYUN_API}')
    payload = {
        'title': title,
        'summary': summary,
        'source': {
            'bvid': video['bvid'],
            'url': f'https://www.bilibili.com/video/{video["bvid"]}',
            'up_uid': video['mid'],
            'up_name': video['author'],
            'published_at': time.strftime('%Y-%m-%d', time.localtime(video['created'])),
        },
    }
    r = requests.post(
        ALIYUN_API,
        json=payload,
        headers={
            'Content-Type': 'application/json',
            'X-Worker-Secret': WORKER_SECRET,
        },
        timeout=120,
    )
    log(f'    HTTP {r.status_code}')
    log(f'    响应: {r.text[:500]}')
    r.raise_for_status()
    return r.json()


def main():
    log('========== 端到端回归测试开始 ==========')
    vlist = get_latest_charged_video()
    if not vlist:
        log('!!! 没有视频')
        sys.exit(1)
    # 找最新一个
    target = vlist[0]
    log(f'    选定视频: {target["title"]} ({target["bvid"]})')
    detail = get_video_detail(target['bvid'])
    rights = detail.get('rights', {})
    is_charged = rights.get('is_charging_arc') == 1 or rights.get('ugc_pay') == 1
    if not is_charged:
        log('!!! 最新视频不是充电视频，退出')
        sys.exit(1)
    log(f'    确认是充电视频')
    cid = detail.get('pages', [{}])[0].get('cid', 0)
    sub = get_subtitle(target['bvid'], cid) if cid else ''
    if not sub:
        log('!!! 没有字幕，退出')
        sys.exit(1)
    summary = call_minimax(target['title'], sub)
    if not summary:
        log('!!! 总结为空，退出')
        sys.exit(1)
    result = push_to_aliyun(target['title'], summary, target)
    log(f'    推送结果: {result}')
    log('========== 完成 ==========')


if __name__ == '__main__':
    main()
