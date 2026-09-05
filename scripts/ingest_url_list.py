"""把一份纯文本 URL 列表（每行一个 mp.weixin.qq.com/s?__biz=...）转成 JSON，
交给 fetch_articles.py 抓正文。

用法:
  python3 ingest_url_list.py urls.txt            # 输出 urls.json
  python3 ingest_url_list.py urls.txt --fetch    # 转换 + 抓取
"""
import asyncio
import json
import os
import sys


def read_urls(txt_path: str) -> list[dict]:
    items: list[dict] = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "mp.weixin.qq.com/s" not in line:
                continue
            items.append({"title": "", "url": line})
    return items


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 ingest_url_list.py <urls.txt> [--fetch] [--out json_path]", flush=True)
        return 1
    src = sys.argv[1]
    fetch = "--fetch" in sys.argv
    out_idx = sys.argv.index("--out") + 1 if "--out" in sys.argv else None
    out = sys.argv[out_idx] if out_idx and out_idx < len(sys.argv) else os.path.splitext(src)[0] + ".json"

    items = read_urls(src)
    print(f"read {len(items)} urls from {src}", flush=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"saved {out}", flush=True)

    if fetch:
        from fetch_articles import main as fetch_main  # type: ignore
        sys.argv = ["fetch_articles.py", out, "/vol2/1000/docker_related/gzh-chroma/articles"]
        asyncio.run(fetch_main(out, "/vol2/1000/docker_related/gzh-chroma/articles"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
