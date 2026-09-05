"""通过 mp_proxy 拉老板公众号 8 篇'过往'已发布文章正文（跳过 v2 风格的最新 3 篇），
存到沙箱 articles/，喂给 scripts/style_bridge.py 总结真实风格。

目标文章（按 publish_time 升序，覆盖 2024-09 → 2026-06-14）：
  [1]  2024-09-27  4天
  [2]  2025-02-14  平地一声雷
  [3]  2025-02-14  惊天大暴涨
  [4]  2025-02-15  平地一声雷
  [5]  2025-04-01  补车票
  [8]  2026-02-08  2026-02-8 每周加餐
  [9]  2026-05-26  今日财经观察｜2026-05-26
  [11] 2026-06-14  特朗普占领哈尔克岛后再次TACO
"""
import http.client
import json
import os
import re
import sys
import time


MP_PROXY = "8.134.248.11"
MP_PORT = 39800
SECRET = os.environ.get('BILIBILI_WORKER_SECRET', '')
OUT_DIR = r"C:\Users\Docker\AppData\Local\Temp\articles"


def post(path, body):
    c = http.client.HTTPConnection(MP_PROXY, MP_PORT, timeout=60)
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    c.request("POST", path, body=payload, headers={
        "Content-Type": "application/json",
        "Content-Length": str(len(payload)),
        "X-Worker-Secret": SECRET,
    })
    r = c.getresponse()
    return json.loads(r.read().decode("utf-8", errors="replace"))


_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.I)
_P_CLOSE = re.compile(r"</p\s*>", re.I)
_IMG = re.compile(r'<img[^>]*?data-src="([^"]+)"[^>]*>', re.I)
_IMG_ALT = re.compile(r'<img[^>]*?>', re.I)
_HR = re.compile(r"</?hr\s*/?>", re.I)
_SECTION = re.compile(r"</?section[^>]*>", re.I)


def html_to_text(html):
    if not html:
        return ""
    html = _SECTION.sub("\n", html)
    html = _HR.sub("\n---\n", html)
    html = _IMG.sub(lambda m: "\n![image](" + m.group(1) + ")\n", html)
    html = _IMG_ALT.sub("", html)
    html = _BR.sub("\n", html)
    html = _P_CLOSE.sub("\n\n", html)
    html = _TAG.sub("", html)
    text = (
        html.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_name(s):
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", s or "")
    return s[:80].strip("_") or "untitled"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=== 1. 拉已发布列表 ===", flush=True)
    r = post("/api/admin/mp-published", {})
    if not r.get("ok"):
        print("!!", r)
        sys.exit(1)
    items = r.get("items", [])
    print("total:", len(items), flush=True)

    # 选 8 篇：时间升序，跳过 v2 风格污染的（最新 3 篇）和标题空白的
    by_time = sorted(items, key=lambda x: x.get("publish_time", 0))
    chosen = []
    for it in by_time:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        pt = it.get("publish_time", 0)
        # 跳过最新 3 篇（v2 风格，可能污染）
        if pt > 1781000000:  # 大约 2026-06-15 之后
            continue
        chosen.append(it)
        if len(chosen) >= 8:
            break

    print(f"selected {len(chosen)}:", flush=True)
    for i, it in enumerate(chosen):
        pt = it.get("publish_time", 0)
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(pt)) if pt else "?"
        print(f"  [{i+1}] {ts} | {it.get('title','')[:60]}", flush=True)

    saved = []
    for i, it in enumerate(chosen):
        title = it.get("title", "")
        media_id = it.get("media_id", "")
        url = it.get("url", "")
        pt = it.get("publish_time", 0)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pt)) if pt else ""

        print(f"\n[{i+1}/{len(chosen)}] {title}", flush=True)
        print(f"  media_id={media_id[:20]}...", flush=True)

        # mp-article-content 用 article_id 字段（list 返回的字段是 media_id，但值可当 article_id 用）
        rc = post("/api/admin/mp-article-content", {"article_id": media_id})
        if not rc.get("ok"):
            print(f"  ✗ fetch fail: {rc}", flush=True)
            continue
        content_html = rc.get("content", "")
        body = html_to_text(content_html)
        if len(body) < 50:
            print(f"  ✗ body too short ({len(body)} chars)", flush=True)
            continue

        fname = safe_name(title) + ".md"
        fpath = os.path.join(OUT_DIR, fname)

        head = ["# " + title, ""]
        if ts:
            head.append("> 发布时间: " + ts)
            head.append("")
        head.append("> media_id: " + media_id)
        head.append("")
        if url:
            head.append("> 原文链接: " + url)
            head.append("")
        head.append("---\n")
        head.append(body)
        head.append("\n")

        with open(fpath, "w", encoding="utf-8") as f:
            f.write("\n".join(head))
        print(f"  ✓ saved {fname} ({len(body)} chars)", flush=True)
        saved.append({"title": title, "file": fpath, "length": len(body), "publish_time": ts})

        # 避免太频繁
        time.sleep(1)

    manifest = os.path.join(OUT_DIR, "_manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    print(f"\n=== 完成：{len(saved)} 篇入库 ===", flush=True)
    print(f"manifest: {manifest}", flush=True)


if __name__ == "__main__":
    main()
