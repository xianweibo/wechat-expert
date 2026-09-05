"""把 drafts/ 里的 markdown 草稿推到公众号草稿箱（经阿里云 mp_proxy）。

步骤：
  1. 调 /mp-articles-all 拿最近一篇文章的封面图 URL
  2. 调 /mp-material-image-add 把封面图上传到公众号素材库
  3. markdown -> mp-html
  4. 调 /mp-draft-add 推送草稿
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request


ALIYUN = os.environ.get("ALIYUN_APP_URL", "http://8.134.248.11:39800")
SECRET = os.environ.get("BILIBILI_WORKER_SECRET", os.environ.get('BILIBILI_WORKER_SECRET', ''))
DRAFT = "/vol2/1000/docker_related/gzh-chroma/drafts/draft_20260612_BV1bZEr6JEDM.md"


def post(url, body, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Worker-Secret": SECRET,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


_H = re.compile(r"^> 源码?来?.*?:", re.M)
_S = re.compile(r"^> 发布时间:.*$", re.M)
_A = re.compile(r"^> 作者:.*$", re.M)
_D = re.compile(r"^---$", re.M)
_Q = re.compile(r"^> (.+)$", re.M)


def md_to_mp_html(md):
    parts = md.split("---", 1)
    body = parts[1] if len(parts) > 1 else parts[0]
    body = _H.sub("", body)
    body = _S.sub("", body)
    body = _A.sub("", body)
    body = re.sub(r"^# (.+)$", r"\1", body, flags=re.M, count=1)
    body = re.sub(r"^# ", "", body, flags=re.M)
    body = body.replace("&", "&amp;")
    lines = body.split("\n")
    out = []
    para = []
    for ln in lines:
        if ln.startswith("> "):
            if para:
                out.append("<p>" + "\n".join(para).replace("\n", "<br>") + "</p>")
                para = []
            out.append('<p style="color:#888;border-left:3px solid #ccc;padding-left:10px;margin:10px 0;">' + ln[2:] + "</p>")
        elif ln.strip() == "":
            if para:
                out.append("<p>" + "\n".join(para).replace("\n", "<br>") + "</p>")
                para = []
        elif ln.startswith("【") and ln.endswith("】"):
            if para:
                out.append("<p>" + "\n".join(para).replace("\n", "<br>") + "</p>")
                para = []
            out.append("<p><strong>" + ln + "</strong></p>")
        elif ln.strip() == "FYI":
            if para:
                out.append("<p>" + "\n".join(para).replace("\n", "<br>") + "</p>")
                para = []
            out.append("<p><strong>FYI</strong></p>")
        else:
            para.append(ln)
    if para:
        out.append("<p>" + "\n".join(para).replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def strip_title(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return m.group(1).strip() if m else "untitled"


def strip_digest(md):
    parts = md.split("---", 1)
    body = parts[1] if len(parts) > 1 else parts[0]
    body = re.sub(r"^# (.+)$", "", body, flags=re.M, count=1)
    body = re.sub(r"<[^>]+>", "", body)
    body = re.sub(r"\s+", "", body)
    return body[:120]


def main():
    with open(DRAFT, "r", encoding="utf-8") as f:
        md = f.read()

    title = strip_title(md)
    html = md_to_mp_html(md)
    digest = strip_digest(md)
    print("title:", title, flush=True)
    print("digest:", digest, flush=True)
    print("html length:", len(html), flush=True)

    print("\n=== 1) fetch recent article cover url ===", flush=True)
    r = post(ALIYUN + "/api/admin/mp-articles-all", {}, timeout=180)
    if not r.get("ok"):
        print("!! articles-all err:", r, flush=True)
        sys.exit(1)
    articles = r.get("articles", [])
    cover_url = None
    for a in articles:
        cu = a.get("thumb_url")
        if cu:
            cover_url = cu
            break
    if not cover_url:
        print("!! no cover found in any article, abort", flush=True)
        sys.exit(2)
    print("cover_url:", cover_url, flush=True)

    print("\n=== 2) upload cover to MP material ===", flush=True)
    r = post(ALIYUN + "/api/admin/mp-material-image-add",
             {"image_url": cover_url}, timeout=180)
    if not r.get("ok"):
        print("!! image-add err:", r, flush=True)
        sys.exit(3)
    thumb = r.get("media_id")
    print("thumb_media_id:", thumb, flush=True)
    print("cover_url (server):", r.get("url"), flush=True)

    print("\n=== 3) push draft to MP ===", flush=True)
    body = {
        "title": title,
        "content": html,
        "author": "小喇叭大只讲",
        "digest": digest,
        "thumb_media_id": thumb,
    }
    r = post(ALIYUN + "/api/admin/mp-draft-add", body, timeout=120)
    if not r.get("ok"):
        print("!! draft-add err:", r, flush=True)
        sys.exit(4)
    new_media_id = r.get("media_id")
    print("OK! media_id:", new_media_id, flush=True)

    print("\n=== 4) delete previous draft if any ===", flush=True)
    log_file = "/vol2/1000/docker_related/gzh-chroma/drafts/_latest_push.json"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            old = json.load(f)
        old_mid = old.get("media_id")
        if old_mid and old_mid != new_media_id:
            r2 = post(ALIYUN + "/api/admin/mp-draft-delete", {"media_id": old_mid}, timeout=30)
            if r2.get("ok"):
                print("deleted old draft:", old_mid, flush=True)
            else:
                print("delete old draft err:", r2, flush=True)
        else:
            print("no old draft to delete", flush=True)

    print("\nnow visible at: https://mp.weixin.qq.com/  (Content > Drafts)", flush=True)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"title": title, "media_id": new_media_id, "thumb": thumb,
                   "cover": cover_url, "digest": digest}, f, ensure_ascii=False, indent=2)
    print("logged to " + log_file, flush=True)


if __name__ == "__main__":
    main()
