"""通过 mp_proxy 拉老板公众号最近 10 篇已发布文章正文，存到沙箱 articles/。

不走 playwright（沙箱未装），走 mp_proxy 的两个端点：
  1. POST /api/admin/mp-appmsg-list       -> 拿列表（title / link / content_source_url / create_time / update_time）
  2. POST /api/admin/mp-article-content   -> 对每篇的 content_source_url 拿正文（如果不行则用 list item 里的 content）

输出:
  z:\代码\养龙虾\公众号专家\articles\<safe_title>.md
  z:\代码\养龙虾\公众号专家\articles\_manifest.json
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error


MP_PROXY = "http://8.134.248.11:39800"
SECRET = "cBsFHdghYA1W07VpultIKEynOSQwNM8z"
OUT_DIR = r"z:\代码\养龙虾\公众号专家\articles"
COUNT = 10


def post(path, body):
    req = urllib.request.Request(
        MP_PROXY + path,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Worker-Secret": SECRET,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
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
    html = _IMG.sub(lambda m: f"\n![image]({m.group(1)})\n", html)
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

    print("=== 1. /mp-appmsg-list (count=20) ===", flush=True)
    r = post("/api/admin/mp-appmsg-list", {"begin": 0, "count": 20})
    if not r.get("ok"):
        print(f"!! {r}")
        sys.exit(1)
    items = r.get("items", [])
    print(f"total={r.get('total')} items={len(items)}", flush=True)
    if not items:
        print("没有任何已发布文章", flush=True)
        return

    # mp_appmsg_list 返回字段：title, link (mp.weixin.qq.com url), content_source_url, create_time, update_time
    # 不返回正文，要拿正文得用 /mp-article-content
    target = items[:COUNT]
    saved = []
    for i, it in enumerate(target):
        title = it.get("title", "")
        link = it.get("link", "") or it.get("url", "")
        content_source_url = it.get("content_source_url", "")
        article_id = it.get("article_id") or it.get("media_id") or ""
        update_time = it.get("update_time", 0)
        if isinstance(update_time, int) and update_time:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(update_time))
        else:
            ts = ""

        print(f"\n[{i+1}/{len(target)}] {title}", flush=True)
        print(f"  link={link[:80]}", flush=True)
        print(f"  content_source_url={content_source_url[:80]}", flush=True)

        body_html = ""

        # 优先尝试 /mp-article-content（如果 article_id 有）
        if article_id:
            try:
                r2 = post("/api/admin/mp-article-content", {"article_id": article_id})
                if r2.get("ok"):
                    body_html = r2.get("content", "")
                    print(f"  ✓ content via mp-article-content ({len(body_html)} chars)", flush=True)
            except Exception as e:
                print(f"  mp-article-content err: {e}", flush=True)

        # 备用：item 自身可能带 content（不太可能，但兜底）
        if not body_html:
            body_html = it.get("content", "") or it.get("digest", "")
            if body_html:
                print(f"  ✓ content via item.content ({len(body_html)} chars)", flush=True)

        if not body_html:
            print(f"  ✗ no content (需要 playwright 抓公开链接，沙箱没装)", flush=True)
            continue

        body = html_to_text(body_html)
        if len(body) < 50:
            print(f"  ✗ body too short ({len(body)} chars), skip", flush=True)
            continue

        fname = f"{safe_name(title)}.md"
        fpath = os.path.join(OUT_DIR, fname)

        head = [f"# {title}", ""]
        if ts:
            head.append(f"> 发布时间: {ts}")
            head.append("")
        if link:
            head.append(f"> 原文链接: {link}")
            head.append("")
        if content_source_url:
            head.append(f"> 原始来源: {content_source_url}")
            head.append("")
        head.append("---\n")
        head.append(body)
        head.append("\n")

        with open(fpath, "w", encoding="utf-8") as f:
            f.write("\n".join(head))
        print(f"  ✓ saved {fpath} ({len(body)} chars)", flush=True)
        saved.append({"title": title, "file": fpath, "length": len(body), "url": link, "publish_time": ts})

    manifest = os.path.join(OUT_DIR, "_manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    print(f"\n=== 完成：{len(saved)} 篇入库 ===", flush=True)
    print(f"manifest: {manifest}", flush=True)


if __name__ == "__main__":
    main()
