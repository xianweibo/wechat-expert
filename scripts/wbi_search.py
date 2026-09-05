import hashlib
import json
import time
import urllib.parse
import urllib.request

SESSDATA = "9fb95afb,1795256344,43e54*51CjAlmSYF2CH2QPDlel40zhHknLUG0zLS9x1C8VJBhYlvj-igRAJ42mi24uxddTIE5FkSVldMZmFrQXFDOTl1OTJGdVVVaUtXY0RJOUFFcFJTV01heFBuSnNtLXdQNzdxdzVrall4Tk0tWEZ5S25RMmpmRWR6c3FBTXh5ZU9vckpKX1JLMHdMVFh3IIEC"

MIXIN_KEY_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
]


def get_mixin_key(img_url, sub_url):
    raw = (img_url + sub_url).rsplit("/", 1)[-1]
    raw = raw.rsplit(".", 1)[0]
    return "".join(raw[i] for i in MIXIN_KEY_TAB if i < len(raw))[:32]


def wbi_sign(params, mixin_key):
    params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
    params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(params)
    w_rid = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    params["w_rid"] = w_rid
    return params


def fetch(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
    "Cookie": "SESSDATA=" + SESSDATA,
}

nav = fetch("https://api.bilibili.com/x/web-interface/nav", H)
img_url = nav["data"]["wbi_img"]["img_url"]
sub_url = nav["data"]["wbi_img"]["sub_url"]
mixin = get_mixin_key(img_url, sub_url)
print("mixin_key:", mixin)

params = {"mid": 290663424, "ps": 30, "pn": 1, "order": "pubdate", "wts": int(time.time())}
signed = wbi_sign(params, mixin)
qs = urllib.parse.urlencode(signed)
url = "https://api.bilibili.com/x/space/wbi/arc/search?" + qs
print("GET", url, flush=True)
try:
    res = fetch(url, H)
    print("code:", res.get("code"), "msg:", res.get("message"))
    vl = res.get("data", {}).get("list", {}).get("vlist", [])
    for v in vl[:5]:
        print("  -", v.get("bvid"), "|", v.get("title")[:50], "|", v.get("created"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8", errors="replace")[:300])
