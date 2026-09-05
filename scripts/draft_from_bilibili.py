#!/usr/bin/env python3
"""端到端：找 UP 主最新充电视频 -> 下载字幕 -> 总结 + 改写成小喇叭大只讲风格 -> 存草稿。

运行在 NAS 上，依赖：
  - ~/.local/bin/yutto  (B站下载器)
  - env: BILIBILI_SESSDATA / BILIBILI_BILI_JCT / MINIMAX_API_KEY / NAS_GZH_DIR
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime


UP_UID = 290663424
MINIMAX_API_KEY = os.environ.get(
    "MINIMAX_API_KEY",
    "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo",
)
SESSDATA = os.environ.get(
    "BILIBILI_SESSDATA",
    "9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC",
)
JCT = os.environ.get("BILIBILI_BILI_JCT", "de6ed23d674a50a73865adae67069017")

STYLE_PATH = "/vol2/1000/docker_related/gzh-chroma/style_summary.txt"
OUT_DIR = "/vol2/1000/docker_related/gzh-chroma/drafts"

MINIMAX_HOST = "api.minimaxi.com"
EMBED_URL = "https://api.minimaxi.com/v1/embeddings"
CHAT_URL = "/anthropic/v1/messages"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}


def get_latest_charged_via_dynamic(uid):
    offset = ""
    for _ in range(3):
        url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(
            url, headers={**HEADERS, "Cookie": f"SESSDATA={SESSDATA}; bili_jct={JCT}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print("dynamic api err:", e, flush=True)
            break
        if d.get("code") != 0:
            print("dynamic code:", d.get("code"), d.get("message"), flush=True)
            break
        items = d.get("data", {}).get("items", [])
        for it in items:
            major = it.get("modules", {}).get("module_dynamic", {}).get("major")
            if not major:
                continue
            archive = major.get("archive", {})
            bvid = archive.get("bvid", "")
            if not bvid:
                continue
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                    headers={**HEADERS, "Cookie": f"SESSDATA={SESSDATA}; bili_jct={JCT}"},
                ),
                timeout=15,
            ) as r2:
                det = json.loads(r2.read().decode("utf-8")).get("data", {})
            rights = det.get("rights", {})
            if rights.get("is_charging_arc") == 1 or rights.get("ugc_pay") == 1:
                ctime = archive.get("ctime") or det.get("pubdate", 0)
                return {
                    "bvid": bvid,
                    "title": archive.get("title") or det.get("title", ""),
                    "desc": det.get("desc", ""),
                    "pubdate": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M") if ctime else "",
                    "duration": det.get("duration", 0),
                }
        if not d.get("data", {}).get("has_more"):
            break
        offset = d.get("data", {}).get("offset", "")
        time.sleep(0.3)
    return None


def get_latest_charged_via_search(uid):
    url = f"https://api.bilibili.com/x/space/arc/search?mid={uid}&ps=30&pn=1&order=pubdate"
    req = urllib.request.Request(
        url, headers={**HEADERS, "Cookie": f"SESSDATA={SESSDATA}; bili_jct={JCT}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    vlist = d.get("data", {}).get("list", {}).get("vlist", [])
    for v in vlist:
        bv = v["bvid"]
        with urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.bilibili.com/x/web-interface/view?bvid={bv}",
                headers={**HEADERS, "Cookie": f"SESSDATA={SESSDATA}; bili_jct={JCT}"},
            ),
            timeout=15,
        ) as r2:
            det = json.loads(r2.read().decode("utf-8")).get("data", {})
        rights = det.get("rights", {})
        if rights.get("is_charging_arc") == 1 or rights.get("ugc_pay") == 1:
            ctime = v.get("created", 0)
            return {
                "bvid": bv,
                "title": v["title"],
                "desc": det.get("desc", ""),
                "pubdate": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M") if ctime else "",
                "duration": det.get("duration", 0),
            }
    return None


def get_latest_charged():
    print("looking up latest paid video via dynamic API...", flush=True)
    v = get_latest_charged_via_dynamic(UP_UID)
    if v:
        return v
    print("fallback to space/arc/search API...", flush=True)
    return get_latest_charged_via_search(UP_UID)


def download_subtitle(bvid):
    print(f"downloading subtitle for {bvid} via yutto...", flush=True)
    tmpdir = tempfile.mkdtemp(prefix="yutto_")
    cmd = (
        f"~/.local/bin/yutto "
        f"--auth 'SESSDATA={SESSDATA};bili_jct={JCT}' "
        f"--subtitle-only "
        f"https://www.bilibili.com/video/{bvid} "
        f"-d {tmpdir} -b"
    )
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    print("yutto stdout:", proc.stdout[-500:], flush=True)
    if proc.returncode != 0:
        print("yutto stderr:", proc.stderr[-500:], flush=True)

    srt_files = []
    for root, _, files in os.walk(tmpdir):
        for fn in files:
            if fn.endswith(".srt"):
                srt_files.append(os.path.join(root, fn))
    if not srt_files:
        raise RuntimeError("no srt file found in " + tmpdir)
    srt = srt_files[0]
    print("subtitle file:", srt, flush=True)
    txt = ""
    with open(srt, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "-->" in line or line.isdigit():
                continue
            txt += line + "\n"
    return txt, tmpdir


def call_minimax(system, user, model="MiniMax-M2.7", max_tokens=4096):
    import http.client
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }, ensure_ascii=False).encode("utf-8")
    conn = http.client.HTTPSConnection(MINIMAX_HOST, timeout=240)
    conn.request(
        "POST", CHAT_URL, body=body,
        headers={
            "x-api-key": MINIMAX_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    conn.close()
    obj = json.loads(data)
    parts = []
    for c in obj.get("content", []):
        if isinstance(c, dict) and c.get("type") == "text":
            parts.append(c.get("text", ""))
    return "".join(parts)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(STYLE_PATH):
        print("!! style summary not found:", STYLE_PATH, flush=True)
        sys.exit(2)
    with open(STYLE_PATH, "r", encoding="utf-8") as f:
        style_block = f.read()

    info = get_latest_charged()
    if not info:
        print("!! no paid video found", flush=True)
        sys.exit(3)
    print("latest paid video:", info, flush=True)

    subtitle, tmpdir = download_subtitle(info["bvid"])
    print(f"subtitle length: {len(subtitle)} chars", flush=True)
    with open(os.path.join(OUT_DIR, "_latest_subtitle.txt"), "w", encoding="utf-8") as f:
        f.write(subtitle)

    print("\n=== step 1: extract key points (neutral) ===", flush=True)
    summary_prompt = (
        "请根据以下B站视频字幕，提取核心观点，整理成结构化的要点笔记。\n\n"
        "要求：\n"
        "1. 列出 5-8 个核心观点/事件\n"
        "2. 每个观点 100-200 字\n"
        "3. 保留关键数据、人名、机构名\n"
        "4. 不要预测涨跌，不要写'总结'\n\n"
        "字幕：\n" + subtitle[:20000]
    )
    bullets = call_minimax(
        "你是一个高效的财经内容编辑，擅长把长视频浓缩成结构化笔记。",
        summary_prompt,
        max_tokens=3000,
    )
    print(bullets[:500], "...", flush=True)
    with open(os.path.join(OUT_DIR, "_latest_bullets.txt"), "w", encoding="utf-8") as f:
        f.write(bullets)

    print("\n=== step 2: rewrite in 小喇叭大只讲 style ===", flush=True)
    style_prompt = (
        "你是公众号【小喇叭大只讲】作者，笔名也是【村级三好大叔】/【有何高见9527】。"
        "你看完 B 站充电视频后，把精华用自己的口吻改写成公众号文章。\n\n"
        "【你的写作口吻（务必严格遵守）】\n" + style_block + "\n\n"
        "【本次视频标题】\n" + info["title"] + "\n\n"
        "【本次视频的要点笔记】\n" + bullets + "\n\n"
        "【写作要求】\n"
        "1. 1000 字左右（不少于 800 字，不多于 1300 字）\n"
        "2. 必须用你自己的标志性开头套路（不要用'总结如下'这种书面语）\n"
        "3. 必须用你自己的标志性结尾套路 + 免责声明三连\n"
        "4. 段落到段落到段落之间节奏要短促有力\n"
        "5. 适度用'咱们''坐稳扶好''好样的''等着''补车票'这类口头禅\n"
        "6. 引用视频里的关键数据、人名、机构名要原样保留\n"
        "7. 不要用 emoji 装饰、不要 markdown 标题层级（公众号正文就是纯文字 + 必要换行）\n"
        "8. 标题单独一行（用 # 标题）\n\n"
        "请直接输出完整文章（标题 + 正文 + 免责声明）。"
    )
    draft = call_minimax(
        "你是【小喇叭大只讲】，写公众号财经文章。",
        style_prompt,
        max_tokens=4096,
    )
    print("\n=== DRAFT ===\n", draft[:1000], "...\n", flush=True)

    fname = "draft_" + info["pubdate"].replace("-", "").replace(" ", "_").replace(":", "") + "_" + info["bvid"] + ".md"
    fpath = os.path.join(OUT_DIR, fname)
    meta = (
        "# " + info["title"] + "\n\n"
        "> 来源视频: https://www.bilibili.com/video/" + info["bvid"] + "\n"
        "> 发布时间: " + info["pubdate"] + "\n"
        "> 作者: 小喇叭大只讲（村级三好大叔）\n\n"
        "---\n\n"
    )
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(meta + draft + "\n")
    print("\nsaved to:", fpath, flush=True)

    meta2 = {"video": info, "file": fpath, "bullets_file": os.path.join(OUT_DIR, "_latest_bullets.txt")}
    with open(os.path.join(OUT_DIR, "_latest_info.json"), "w", encoding="utf-8") as f:
        json.dump(meta2, f, ensure_ascii=False, indent=2)
    print("done.", flush=True)


if __name__ == "__main__":
    main()
