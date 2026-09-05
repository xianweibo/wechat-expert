import json
import os
import urllib.request


H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.cls.cn/",
}

urls = [
    "https://www.cls.cn/detail/2395116",
    "https://www.cls.cn/detail/2393814",
]
for u in urls:
    req = urllib.request.Request(u, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
            print("=== " + u + " ===", flush=True)
            print("len=" + str(len(html)), flush=True)
            # extract article body
            start = html.find("article-content")
            if start < 0:
                start = html.find("rich-content")
            if start < 0:
                start = html.find("subject-content")
            if start < 0:
                # fallback: print first 3000 chars
                print(html[:5000], flush=True)
            else:
                print(html[start:start + 6000], flush=True)
            print(flush=True)
    except Exception as e:
        print("ERR " + u + ": " + str(e), flush=True)
