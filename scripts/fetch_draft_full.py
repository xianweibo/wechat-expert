import os
import json
import subprocess
import sys
from typing import List, Optional, Dict, Any

APP_ID = "wx567a639466e247cd"
APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '')
OUT_JSON = "/tmp/mp_articles_full.json"
OUT_INDEX = "/tmp/mp_articles_index.json"
CONTAINER_FILTER = "gzh-expert-app"
DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/batchget"


def container_id():
    out = subprocess.check_output(
        ["docker", "ps", "--filter", "name=" + CONTAINER_FILTER, "-q"],
        universal_newlines=True,
    )
    return out.split()[0] if out.strip() else ""


def wget_in_container(c, url, body=None):
    cmd = ["docker", "exec", c, "wget", "-qO-"]
    if body is not None:
        cmd += ["--header=Content-Type: application/json", "--post-data=" + body]
    cmd.append(url)
    return subprocess.check_output(cmd, universal_newlines=True)


def main():
    c = container_id()
    if not c:
        print("no container found", file=sys.stderr)
        return 1
    print("container=" + c)

    tok_url = (
        "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid="
        + APP_ID + "&secret=" + APP_SECRET
    )
    tok_json = wget_in_container(c, tok_url)
    token = json.loads(tok_json).get("access_token", "")
    if not token:
        print("token err: " + tok_json, file=sys.stderr)
        return 2
    print("token=" + token[:20] + "...")

    all_items = []
    offset = 0
    count = 5
    total = None
    while True:
        body = json.dumps({"offset": offset, "count": count, "no_content": 0})
        url = DRAFT_URL + "?access_token=" + token
        raw = wget_in_container(c, url, body)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print("json err: " + str(e) + " raw=" + raw[:300], file=sys.stderr)
            return 3
        if data.get("errcode"):
            print("API err: " + str(data), file=sys.stderr)
            return 4
        if total is None:
            total = data.get("total_count", 0)
            print("total_count=" + str(total))
        items = data.get("item") or data.get("item_list") or data.get("items") or []
        print("offset=" + str(offset) + " got=" + str(len(items)))
        all_items.extend(items)
        offset += len(items)
        if not items or len(items) < count or (total is not None and offset >= total):
            break

    print("collected " + str(len(all_items)) + " items")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print("saved " + OUT_JSON)

    index = []
    for it in all_items:
        news_items = (it.get("content", {}) or {}).get("news_item", []) or [it]
        for ni in news_items:
            title = ni.get("title", "")
            author = ni.get("author", "")
            digest = ni.get("digest", "")
            content_html = ni.get("content", "")
            url_ = ni.get("url", "")
            ts = ni.get("update_time") or it.get("update_time") or 0
            index.append({
                "title": title,
                "author": author,
                "digest": digest,
                "url": url_,
                "publish_time": ts,
                "content_len": len(content_html),
            })
    with open(OUT_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("saved " + OUT_INDEX + " (" + str(len(index)) + " entries)")
    for e in index:
        print(
            "  - "
            + str(e["publish_time"])
            + " | "
            + e["title"][:40].ljust(40)
            + " | "
            + str(e["content_len"]).rjust(5)
            + " chars | "
            + str(e["author"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
