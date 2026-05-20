#!/usr/bin/env python3
import json
import os
import sys
import requests
import subprocess
import tempfile

# 配置
MINIMAX_API_KEY = "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo"
API_BASE = "http://127.0.0.1:39800"
YUTTO_AUTH = "SESSDATA=6c8d910f,1779246988,c0f28*51CjCgiuLwxLl2W0_wCeUQE2phXSsrBmkgjT8W0NQKSCMJglKqfUQofOul7aleq7YzWnASVkw5WG8tYUpOMXZfbEQ1NHlCUmdkMHVQbnJlUS1yNzBvWU5RYVltMGEyelUtTURiSEFEeXRWdHJKWFFPbXdlOWEyWEJSeVhielkxcVpoYUdQTEtTMEpBIIEC;bili_jct=84b14a38d9df625098c9fe7fe338b421"

def download_subtitle(bvid: str) -> str:
    """下载B站视频字幕"""
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
    
    # 找到下载的srt文件
    srt_files = []
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file.endswith(".srt"):
                srt_files.append(os.path.join(root, file))
    
    if not srt_files:
        raise Exception("未找到下载的字幕文件")
    
    # 读取字幕内容
    content = ""
    with open(srt_files[0], "r", encoding="utf-8") as f:
        lines = f.readlines()
        # 过滤掉时间线和空行
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

def summarize_content(content: str) -> dict:
    """调用MiniMax总结内容"""
    print("开始调用MiniMax总结内容...")
    prompt = f"""
你是一个专业的财经内容编辑，请根据下面的B站视频字幕，生成适合公众号发布的内容。
要求：
1. 提取核心观点，分3-5个要点
2. 语言通俗易懂，适合大众阅读
3. 保持中立，不做投资建议
4. 总字数控制在300-500字
5. 输出格式为JSON，包含title（标题）和content（正文）两个字段

字幕内容：
{content}
"""
    url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "MiniMax-Text-01",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()
        # 尝试解析JSON
        try:
            return json.loads(reply)
        except:
            # 如果解析失败，直接返回文本
            return {
                "title": "今日财经要点",
                "content": reply
            }
    except Exception as e:
        print(f"MiniMax调用失败: {str(e)}")
        raise

def push_to_cloud(content: dict, bvid: str) -> bool:
    """推送到阿里云API"""
    print("开始推送到阿里云...")
    try:
        url = f"{API_BASE}/api/bilibili/submit"
        data = {
            "bvid": bvid,
            "title": content["title"],
            "content": content["content"],
            "source_url": f"https://www.bilibili.com/video/{bvid}"
        }
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            print(f"推送成功，草稿ID：{result.get('draft_id')}")
            return True
        else:
            print(f"推送失败：{result.get('message')}")
            return False
    except Exception as e:
        print(f"推送失败: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python3 bilibili_worker.py <BV号>")
        print("示例: python3 bilibili_worker.py BV191Lu64EWD")
        return
    
    bvid = sys.argv[1]
    if not bvid.startswith("BV"):
        print("BV号格式错误，应该以BV开头")
        return
    
    try:
        # 1. 下载字幕
        content = download_subtitle(bvid)
        # 2. 总结内容
        summary = summarize_content(content)
        print(f"生成的标题：{summary['title']}")
        print(f"生成的内容：\n{summary['content']}")
        # 3. 推送
        success = push_to_cloud(summary, bvid)
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
