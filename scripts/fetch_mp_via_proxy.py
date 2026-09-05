"""通过阿里云 app 代理拉公众号发表记录（解决 IP 白名单问题）。

不直接调 MP API，所有 MP API 调用都转发到阿里云的 gzh-expert-app：
  POST {ALIYUN_APP_URL}/api/admin/mp-articles-all   -> 一次性拉所有文章 + 全文
  POST {ALIYUN_APP_URL}/api/admin/mp-published     -> 仅列表（轻量）

应用从阿里云发请求，IP 已在 MP 白名单中。
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


ALIYUN_APP_URL = os.environ.get(
    "ALIYUN_APP_URL", "http://8.134.248.11:39800"
)
WORKER_SECRET = os.environ.get("BILIBILI_WORKER_SECRET", "")
OUT_DIR = os.environ.get(
    "ARTICLES_DIR", "/vol2/1000/docker_related/gzh-chroma/articles"
)


def post_json(url, body, headers=None, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    h = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.I)
_P_CLOSE = re.compile(r"</p\s*>", re.I)
_IMG = re.compile(r'<img[^>]*?data-src="([^"]+)"[^>]*>', re.I)
_IMG_ANY = re.compile(r'<img[^>]*>', re.I)
_HR = re.compile(r"</?hr\s*/?>", re.I)
_SECTION = re.compile(r"</?section[^>]*>", re.I)
_STRONG = re.compile(r"<(strong|b)>(.*?)</\1>", re.I | re.S)
_EM = re.compile(r"<(em|i)>(.*?)</\1>", re.I | re.S)


def html_to_text(html):
    if not html:
        return ""
    html = _SECTION.sub("\n", html)
    html = _HR.sub("\n---\n", html)
    html = _IMG.sub(lambda m: "\n![image](" + m.group(1) + ")\n", html)
    html = _IMG_ANY.sub("", html)
    html = _BR.sub("\n", html)
    html = _P_CLOSE.sub("\n\n", html)
    html = _STRONG.sub(lambda m: "**" + m.group(2) + "**", html)
    html = _EM.sub(lambda m: "*" + m.group(2) + "*", html)
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


_save_counter = {}


def _unique_path(out_dir, base_fname):
    if base_fname not in _save_counter:
        _save_counter[base_fname] = 0
        return os.path.join(out_dir, base_fname)
    _save_counter[base_fname] += 1
    stem, ext = os.path.splitext(base_fname)
    new = stem + "_" + str(_save_counter[base_fname]).zfill(2) + ext
    return os.path.join(out_dir, new)


def save_md(meta, body_html, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    title = meta.get("title") or "untitled"
    publish_time = meta.get("publish_time") or 0
    if isinstance(publish_time, int) and publish_time > 0:
        ts_full = time.strftime("%Y%m%d_%H%M%S", time.localtime(publish_time))
        ts_date = ts_full[:8]
        publish_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(publish_time))
    else:
        ts_full = "00000000_000000"
        ts_date = "00000000"
        publish_time_str = ""
    url = meta.get("url") or ""
    author = meta.get("author") or ""
    digest = meta.get("digest") or ""
    media_id = meta.get("media_id") or ""
    mid_short = media_id[-6:] if media_id else ""

    body = html_to_text(body_html)
    base = safe_name(title)
    stem = ts_date + "_" + base
    if mid_short:
        stem = stem + "_" + mid_short
    fname = stem + ".md"
    fpath = _unique_path(out_dir, fname)

    head = ["# " + title, ""]
    if publish_time_str:
        head.append("> 发布时间: " + publish_time_str)
        head.append("")
    if author:
        head.append("> 作者: " + author)
        head.append("")
    if url:
        head.append("> 原文链接: " + url)
        head.append("")
    if digest:
        head.append("> 摘要: " + digest)
        head.append("")
    if media_id:
        head.append("> media_id: " + media_id)
        head.append("")
    head.append("---")
    head.append("")
    head.append(body)
    head.append("")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(head))
    return {"title": title, "file": fpath, "length": len(body)}


def main():
    if not WORKER_SECRET:
        print("!! BILIBILI_WORKER_SECRET 未设置", file=sys.stderr)
        sys.exit(2)

    auth_headers = {"X-Worker-Secret": WORKER_SECRET}

    print("=== 1. 拉全量文章（含正文）===")
    list_url = ALIYUN_APP_URL.rstrip("/") + "/api/admin/mp-articles-all"
    print("  URL:", list_url)
    try:
        resp = post_json(list_url, {}, auth_headers, timeout=180)
    except urllib.error.URLError as e:
        print("!! 调用失败: " + str(e), file=sys.stderr)
        sys.exit(3)
    if not resp.get("ok"):
        print("!! 接口返回错误: " + str(resp), file=sys.stderr)
        sys.exit(4)

    articles = resp.get("articles", [])
    total = resp.get("total", len(articles))
    print("  total=" + str(total) + " got=" + str(len(articles)))

    if not articles:
        print("  没有文章，退出")
        return

    saved = []
    for i, art in enumerate(articles):
        try:
            r = save_md(art, art.get("content", ""), OUT_DIR)
            print("  [" + str(i + 1) + "/" + str(len(articles)) + "] " + r["title"][:40] + " (" + str(r["length"]) + " chars)")
            saved.append(r)
        except Exception as e:
            print("  [" + str(i + 1) + "] save fail: " + str(e), file=sys.stderr)

    print("\n=== 完成: " + str(len(saved)) + " 篇入库 ===")
    manifest = os.path.join(OUT_DIR, "_manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    print("manifest:", manifest)


if __name__ == "__main__":
    main()
