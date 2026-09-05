"""拉取公众号已发表文章列表 + 正文，存成 markdown 文件。

数据源：WeChat 公众号官方 API（access_token 模式）
    1. GET  /cgi-bin/token                                  -> access_token
    2. POST /cgi-bin/freepublish/list    (新接口, 推荐)     -> 已发表列表
       POST /cgi-bin/freepublish/batchget                  -> 批量取正文 (备用)
    3. POST /cgi-bin/appmsg/list         (老接口兜底)       -> 历史全部

AppID  写死在脚本里（与 SKILL.md 一致）
AppSecret 从 /tmp/.mp_app_secret 读取（与阿里云其他脚本一致）
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


APP_ID = "wx567a639466e247cd"
APP_SECRET_FILE = os.environ.get("MP_APP_SECRET_FILE", "/tmp/.mp_app_secret")

API_BASE = "https://api.weixin.qq.com/cgi-bin"

OUT_DIR = os.environ.get(
    "ARTICLES_DIR", "/vol2/1000/docker_related/gzh-chroma/articles"
)


# ---------- HTTP ----------
def http_get(url, timeout=30):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def http_post(url, body, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


# ---------- access_token ----------
def get_access_token(app_id: str, app_secret: str) -> str:
    url = (
        f"{API_BASE}/token?grant_type=client_credential"
        f"&appid={urllib.parse.quote(app_id)}&secret={urllib.parse.quote(app_secret)}"
    )
    data = http_get(url)
    if "access_token" not in data:
        raise RuntimeError(f"get access_token failed: {data}")
    print(f"  access_token acquired (expires_in={data.get('expires_in')})")
    return data["access_token"]


# ---------- 已发表列表 ----------
def list_freepublish(token: str, max_count: int = 100):
    """新接口：freepublish/list 分页拉取已发表。"""
    out = []
    offset = 0
    page_size = 20
    while True:
        body = {"offset": offset, "count": page_size, "no_content": 1}
        url = f"{API_BASE}/freepublish/list?access_token={urllib.parse.quote(token)}"
        try:
            data = http_post(url, body)
        except urllib.error.HTTPError as e:
            print(f"  freepublish/list HTTP {e.code}: {e.read().decode('utf-8','replace')}")
            break
        if data.get("errcode", 0) not in (0, None):
            print(f"  freepublish/list errcode={data['errcode']} {data.get('errmsg')}")
            break
        items = data.get("news_item", []) or data.get("item", [])
        out.extend(items)
        print(f"  offset={offset} got {len(items)} (total so far {len(out)})")
        if len(items) < page_size or len(out) >= max_count:
            break
        offset += page_size
    return out


def list_appmsg(token: str, max_count: int = 200):
    """老接口兜底：appmsg/list 拿历史全部 (含已发表 + 部分历史群发)。"""
    out = []
    begin = 0
    page_size = 20
    while True:
        url = (
            f"{API_BASE}/appmsg/list?access_token={urllib.parse.quote(token)}"
            f"&begin={begin}&count={page_size}&type=1"
        )
        try:
            data = http_get(url)
        except urllib.error.HTTPError as e:
            print(f"  appmsg/list HTTP {e.code}")
            break
        if data.get("errcode", 0) not in (0, None):
            print(f"  appmsg/list errcode={data['errcode']} {data.get('errmsg')}")
            break
        items = data.get("appmsg_list", [])
        out.extend(items)
        print(f"  begin={begin} got {len(items)} (total so far {len(out)})")
        if "total" in data and len(out) >= data["total"]:
            break
        if len(items) < page_size or len(out) >= max_count:
            break
        begin += page_size
    return out


# ---------- 正文 ----------
def get_freepublish_article(token: str, article_id: str) -> dict:
    """新接口：拿已发表文章 HTML。"""
    url = (
        f"{API_BASE}/freepublish/getarticle?access_token={urllib.parse.quote(token)}"
    )
    body = {"article_id": article_id}
    return http_post(url, body)


# ---------- HTML -> Markdown ----------
_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.I)
_P_CLOSE = re.compile(r"</p\s*>", re.I)
_IMG = re.compile(
    r'<img[^>]*?data-src="([^"]+)"[^>]*>', re.I
)
_IMG_ALT = re.compile(r'<img[^>]*?>', re.I)
_HR = re.compile(r"</?hr\s*/?>", re.I)
_SECTION = re.compile(r"</?section[^>]*>", re.I)


def html_to_text(html: str) -> str:
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


# ---------- 保存 ----------
def safe_name(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", s or "")
    return s[:80].strip("_") or "untitled"


def save_markdown(meta: dict, body_html: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    title = meta.get("title") or "untitled"
    publish_time = meta.get("update_time") or meta.get("publish_time") or ""
    if isinstance(publish_time, int):
        publish_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(publish_time))
    url = meta.get("url") or meta.get("link") or ""

    body = html_to_text(body_html)

    fname = f"{safe_name(title)}.md"
    fpath = os.path.join(out_dir, fname)

    head = [f"# {title}", ""]
    if publish_time:
        head.append(f"> 发布时间: {publish_time}")
        head.append("")
    if url:
        head.append(f"> 原文链接: {url}")
        head.append("")
    head.append("---\n")
    head.append(body)
    head.append("\n")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(head))
    print(f"  saved {fpath} ({len(body)} chars)")
    return {"title": title, "file": fpath, "length": len(body), "url": url, "publish_time": publish_time}


# ---------- main ----------
def main():
    if not os.path.exists(APP_SECRET_FILE):
        print(f"!! 找不到 {APP_SECRET_FILE}，请先 echo '你的AppSecret' > {APP_SECRET_FILE}")
        sys.exit(2)
    app_secret = open(APP_SECRET_FILE).read().strip()
    if not app_secret:
        print(f"!! {APP_SECRET_FILE} 为空")
        sys.exit(2)

    print("=== 1. 获取 access_token ===")
    token = get_access_token(APP_ID, app_secret)

    print("\n=== 2. 拉发表列表（先 freepublish，失败 fallback appmsg）===")
    items = list_freepublish(token)
    list_source = "freepublish"
    if not items:
        items = list_appmsg(token)
        list_source = "appmsg"
    print(f"\n共 {len(items)} 条")
    if not items:
        print("没有任何文章，退出")
        return

    print(f"\n=== 3. 拉正文并存为 markdown (源={list_source}, 输出={OUT_DIR}) ===")
    saved = []
    for i, item in enumerate(items):
        title = item.get("title") or ""
        url = item.get("url") or item.get("link") or ""
        publish_time = item.get("update_time") or item.get("create_time") or 0
        article_id = item.get("article_id") or item.get("media_id") or ""

        body_html = ""
        if list_source == "freepublish" and article_id:
            try:
                resp = get_freepublish_article(token, article_id)
                article_list = resp.get("news_item") or resp.get("article_list") or []
                if article_list:
                    body_html = article_list[0].get("content", "")
            except Exception as e:
                print(f"  [{i+1}] freepublish/getarticle 失败: {e}")

        if not body_html:
            body_html = item.get("content", "") or item.get("digest", "")

        if not body_html:
            print(f"  [{i+1}] skip (no content): {title}")
            continue

        meta = {"title": title, "url": url, "update_time": publish_time}
        try:
            r = save_markdown(meta, body_html, OUT_DIR)
            saved.append(r)
        except Exception as e:
            print(f"  [{i+1}] save fail: {e}")

    manifest_path = os.path.join(OUT_DIR, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    print(f"\n=== 完成：{len(saved)} 篇入库 ===")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()