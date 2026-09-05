import os
import json
import urllib.request

SESSDATA = os.environ.get('BILIBILI_SESSDATA', '')
JCT = "de6ed23d674a50a73865adae67069017"
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}

urls = [
    "https://api.bilibili.com/x/web-interface/nav",
    "https://api.bilibili.com/x/space/wbi/arc/search?mid=290663424&ps=5&pn=1",
    "https://api.bilibili.com/x/space/arc/search?mid=290663424&ps=5&pn=1&order=pubdate",
    "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid=290663424",
]
for u in urls:
    req = urllib.request.Request(u, headers={**H, "Cookie": f"SESSDATA={SESSDATA}; bili_jct={JCT}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
            print("OK", u[:80], "->", d.get("code"), str(d)[:200])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, u[:80], "->", e.read().decode("utf-8", errors="replace")[:300])
    except Exception as e:
        print("ERR", u[:80], "->", str(e)[:200])
