#!/usr/bin/env python3
import json
import os
import sys
import time
import requests
import subprocess
import tempfile
from datetime import datetime

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
API_BASE = os.environ.get("ALIYUN_API_URL", "http://127.0.0.1:39800")
BILIBILI_SESSDATA = os.environ.get("BILIBILI_SESSDATA", "")
BILIBILI_BILI_JCT = os.environ.get("BILIBILI_BILI_JCT", "")
YUTTO_AUTH = f"SESSDATA={BILIBILI_SESSDATA};bili_jct={BILIBILI_BILI_JCT}" if BILIBILI_SESSDATA and BILIBILI_BILI_JCT else ""

UP_UID = 290663424

if not MINIMAX_API_KEY:
    print("错误: 环境变量 MINIMAX_API_KEY 未设置")
    sys.exit(1)

if not YUTTO_AUTH:
    print("错误: 环境变量 BILIBILI_SESSDATA 或 BILIBILI_BILI_JCT 未设置")
    sys.exit(1)

cookies = {'SESSDATA': BILIBILI_SESSDATA, 'bili_jct': BILIBILI_BILI_JCT}
req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': 'https://www.bilibili.com/'}

def get_latest_charged_video():
    print("获取UP主最新充电视频（动态API）...")
    video = _get_latest_charged_from_dynamic()
    if video:
        return video

    print("动态API未找到充电视频，尝试常规API...")
    resp = requests.get(
        f'https://api.bilibili.com/x/space/arc/search?mid={UP_UID}&ps=30&pn=1&order=pubdate',
        cookies=cookies, headers=req_headers, timeout=30
    )
    data = resp.json()
    vlist = data.get('data', {}).get('list', {}).get('vlist', [])
    if not vlist:
        resp2 = requests.get(
            f'https://api.bilibili.com/x/space/wbi/arc/search?mid={UP_UID}&ps=30&pn=1',
            cookies=cookies, headers=req_headers, timeout=30
        )
        data2 = resp2.json()
        vlist = data2.get('data', {}).get('list', {}).get('vlist', [])

    if not vlist:
        return None

    for v in vlist:
        bv = v['bvid']
        try:
            detail_resp = requests.get(
                f'https://api.bilibili.com/x/web-interface/view?bvid={bv}',
                cookies=cookies, headers=req_headers, timeout=15
            )
            detail = detail_resp.json()
            rights = detail.get('data', {}).get('rights', {})
            if rights.get('ugc_pay', 0) == 1 or rights.get('is_charging_arc', 0) == 1:
                pubdate = datetime.fromtimestamp(v.get('created', 0)).strftime('%Y-%m-%d')
                print(f"找到充电视频: {bv} - {v['title']} ({pubdate})")
                return {'bvid': bv, 'title': v['title'], 'pubdate': pubdate}
        except Exception as e:
            print(f"检查 {bv} 失败: {e}")
            continue

    latest = vlist[0]
    pubdate = datetime.fromtimestamp(latest.get('created', 0)).strftime('%Y-%m-%d')
    print(f"未找到充电视频，使用最新视频: {latest['bvid']} - {latest['title']}")
    return {'bvid': latest['bvid'], 'title': latest['title'], 'pubdate': pubdate}


def _get_latest_charged_from_dynamic(max_pages=3):
    offset = ''
    for page in range(max_pages):
        url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={UP_UID}'
        if offset:
            url += f'&offset={offset}'
        try:
            resp = requests.get(url, cookies=cookies, headers=req_headers, timeout=15)
            data = resp.json()
            if data.get('code') != 0:
                print(f"动态API返回错误: code={data.get('code')}, msg={data.get('message')}")
                break

            items = data.get('data', {}).get('items', [])
            if not items:
                print("动态列表为空")
                break

            for item in items:
                major = item.get('modules', {}).get('module_dynamic', {}).get('major')
                if not major:
                    continue
                archive = major.get('archive', {})
                bvid = archive.get('bvid', '')
                if not bvid:
                    continue

                try:
                    detail_resp = requests.get(
                        f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
                        cookies=cookies, headers=req_headers, timeout=15
                    )
                    detail = detail_resp.json()
                    rights = detail.get('data', {}).get('rights', {})
                    if rights.get('is_charging_arc', 0) == 1 or rights.get('ugc_pay', 0) == 1:
                        title = archive.get('title', detail.get('data', {}).get('title', ''))
                        ctime = archive.get('ctime', 0)
                        pubdate = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d') if ctime else datetime.now().strftime('%Y-%m-%d')
                        print(f"找到充电视频: {bvid} - {title} ({pubdate})")
                        return {'bvid': bvid, 'title': title, 'pubdate': pubdate}
                except Exception as e:
                    print(f"检查 {bvid} 失败: {e}")
                    continue

            has_more = data.get('data', {}).get('has_more', False)
            offset = data.get('data', {}).get('offset', '')
            if not has_more or not offset:
                print("动态列表已到底")
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"动态API请求失败: {e}")
            break

    return None

def download_subtitle(bvid: str) -> str:
    print(f"开始下载视频 {bvid} 的字幕...")
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "~/.local/bin/yutto",
            "--auth", YUTTO_AUTH,
            "--subtitle-only",
            f"https://www.bilibili.com/video/{bvid}",
            "-d", tmpdir,
            "-b"
        ]
        try:
            subprocess.run(" ".join(cmd), shell=True, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"字幕下载失败: {e.stderr}")
            raise

    srt_files = []
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file.endswith(".srt"):
                srt_files.append(os.path.join(root, file))

    if not srt_files:
        raise Exception("未找到下载的字幕文件")

    content = ""
    with open(srt_files[0], "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            content += line + "\n"

    print(f"字幕下载成功，共 {len(content)} 字符")
    return content

def summarize_content(content: str) -> str:
    print("开始调用MiniMax总结内容...")
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
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        summary = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                summary = item.get("text", "")
                break
        if not summary:
            summary = result["choices"][0]["message"]["content"].strip()
        return summary
    except Exception as e:
        print(f"MiniMax调用失败: {str(e)}")
        raise

def push_to_cloud(title: str, summary: str, bvid: str, pubdate: str) -> bool:
    print("开始推送到阿里云...")
    try:
        url = f"{API_BASE}/api/bilibili/summary"
        data = {
            "title": title,
            "summary": summary,
            "source": {
                "bvid": bvid,
                "url": f"https://www.bilibili.com/video/{bvid}",
                "up_uid": UP_UID,
                "up_name": "",
                "published_at": pubdate
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Worker-Secret": os.environ.get("BILIBILI_WORKER_SECRET", "")
        }
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            print(f"推送成功，草稿ID：{result.get('media_id')}")
            return True
        else:
            print(f"推送失败：{result.get('message')}")
            return False
    except Exception as e:
        print(f"推送失败: {str(e)}")
        return False

def main():
    bvid = None
    title = None
    pubdate = None

    if len(sys.argv) >= 2 and sys.argv[1].startswith("BV"):
        bvid = sys.argv[1]
        title = "手动指定"
        pubdate = datetime.now().strftime('%Y-%m-%d')
    else:
        video_info = get_latest_charged_video()
        if not video_info:
            print("无法获取视频信息")
            sys.exit(1)
        bvid = video_info['bvid']
        title = video_info['title']
        pubdate = video_info['pubdate']

    print(f"目标视频: {bvid} - {title}")

    try:
        content = download_subtitle(bvid)
        summary = summarize_content(content)
        print(f"生成的标题：{title}")
        print(f"生成的内容 ({len(summary)} 字)：\n{summary}")
        success = push_to_cloud(title, summary, bvid, pubdate)
        if success:
            print("✅ 任务完成！")
            sys.exit(0)
        else:
            print("❌ 推送失败")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 任务失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
