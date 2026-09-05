"""把 articles/ 下所有历史文章向量化存到 NAS gzh-chroma。

Chroma v2 API 不会自动 embed，所以走 MiniMax embo-01（1536 维）。
"""
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid


CHROMA_BASE = os.environ.get("CHROMA_BASE", "http://127.0.0.1:8100")
TENANT = "default_tenant"
DATABASE = "default_database"
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION", "gzh_articles")
ARTICLES_DIR = os.environ.get("ARTICLES_DIR", "/vol2/1000/docker_related/gzh-chroma/articles")

MINIMAX_API_KEY = os.environ.get(
    "MINIMAX_API_KEY",
    "sk-cp-w8aacTTOBqlc9U42O6cf4oc79uUyXuD5DZRO6ZoY4Zh09qQR31q5AgWKdlV9JaRBRQ_u8QSJe_CsPY936nEzMQ3J0exlNQ71c9958P4i9xNjd8cWD3Cyjlo",
)
EMBED_URL = "https://api.minimaxi.com/v1/embeddings"
EMBED_MODEL = "embo-01"
EMBED_BATCH = 16

CHROMA_PREFIX = (
    f"/api/v2/tenants/{TENANT}/databases/{DATABASE}"
)


def chroma(method, path, body=None, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        CHROMA_BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode("utf-8", errors="replace")
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        return {"_error": True, "_status": e.code, "_body": e.read().decode("utf-8", errors="replace")[:300]}


def embed_batch(texts):
    body = {"model": EMBED_MODEL, "texts": texts, "type": "db"}
    req = urllib.request.Request(
        EMBED_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={
            "Authorization": "Bearer " + MINIMAX_API_KEY,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode("utf-8"))
        return d["vectors"]


def chunk_text(text, max_chars=1200, overlap=150):
    chunks = []
    text = (text or "").strip()
    if not text:
        return chunks
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def get_or_create_collection():
    listing = chroma("GET", CHROMA_PREFIX + "/collections")
    for c in listing or []:
        if c.get("name") == COLLECTION_NAME:
            return c["id"]
    res = chroma("POST", CHROMA_PREFIX + "/collections",
                 {"name": COLLECTION_NAME, "metadata": {"hnsw:space": "cosine"}})
    if res.get("_error"):
        print("create collection err:", res, flush=True)
        raise SystemExit(3)
    return res["id"]


def main():
    md_files = sorted(glob.glob(os.path.join(ARTICLES_DIR, "*.md")))
    md_files = [f for f in md_files if not os.path.basename(f).startswith("_")]
    print("found " + str(len(md_files)) + " articles", flush=True)
    if not md_files:
        return

    coll_id = get_or_create_collection()
    print("collection id: " + coll_id, flush=True)

    total_chunks = 0
    total_articles = 0
    for fp in md_files:
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()
        title = ""
        author = ""
        publish_time = ""
        url = ""
        media_id = ""
        lines = text.split("\n", 30)
        for line in lines:
            ls = line.strip()
            if ls.startswith("# "):
                title = ls[2:].strip()
            elif ls.startswith("> 作者:"):
                author = ls.split(":", 1)[1].strip()
            elif ls.startswith("> 发布时间:"):
                publish_time = ls.split(":", 1)[1].strip()
            elif ls.startswith("> 原文链接:"):
                url = ls.split(":", 1)[1].strip()
            elif ls.startswith("> media_id:"):
                media_id = ls.split(":", 1)[1].strip()
            elif ls == "---":
                break
        body_start = text.find("---")
        body = text[body_start + 3:].strip() if body_start >= 0 else text

        chunks = chunk_text(body, max_chars=1200, overlap=150)
        if not chunks:
            print("  skip (empty): " + os.path.basename(fp), flush=True)
            continue

        all_embeddings = []
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[i:i + EMBED_BATCH]
            vecs = embed_batch(batch)
            all_embeddings.extend(vecs)
            print("    embed " + str(i + len(batch)) + "/" + str(len(chunks)), flush=True)
            time.sleep(0.1)

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {
                "source_file": os.path.basename(fp),
                "title": title or os.path.basename(fp),
                "author": author,
                "publish_time": publish_time,
                "url": url,
                "media_id": media_id,
                "chunk_index": idx,
                "total_chunks": len(chunks),
            }
            for idx in range(len(chunks))
        ]
        res = chroma("POST", CHROMA_PREFIX + "/collections/" + coll_id + "/add",
                     {"ids": ids, "embeddings": all_embeddings,
                      "documents": chunks, "metadatas": metadatas})
        if res.get("_error"):
            print("  FAIL " + os.path.basename(fp) + ": " + str(res), flush=True)
            continue
        total_chunks += len(chunks)
        total_articles += 1
        print("  ok " + os.path.basename(fp) + ": " + str(len(chunks)) + " chunks", flush=True)

    print("\n=== " + str(total_articles) + " articles, " + str(total_chunks) + " chunks ingested ===", flush=True)


if __name__ == "__main__":
    main()
