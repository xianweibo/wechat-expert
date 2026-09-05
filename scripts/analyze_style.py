"""RAG 风格口吻 prompt：先从 gzh-chroma 检索相似文章片段，再喂给 MiniMax-M3。"""
import json
import os
import sys
import urllib.error
import urllib.request


CHROMA_BASE = os.environ.get("CHROMA_BASE", "http://127.0.0.1:8100")
TENANT = "default_tenant"
DATABASE = "default_database"
COLLECTION = os.environ.get("CHROMA_COLLECTION", "gzh_articles")
COLL_ID = os.environ.get("CHROMA_COLL_ID", "a47e1cf2-325c-4f8f-8892-d9cc290cd93f")
MINIMAX_KEY = os.environ.get(
    "MINIMAX_API_KEY",
    os.environ.get('MINIMAX_API_KEY', ''),
)
MINIMAX_HOST = os.environ.get("MINIMAX_HOST", "api.minimaxi.com")
MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
EMBED_MODEL = "embo-01"
EMBED_URL = "https://api.minimaxi.com/v1/embeddings"
QUERY_N_RESULTS = 10


def embed_query(text):
    body = {"model": EMBED_MODEL, "texts": [text], "type": "query"}
    req = urllib.request.Request(
        EMBED_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={
            "Authorization": "Bearer " + MINIMAX_KEY,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
        return d["vectors"][0]


def chroma_query(query_emb, n_results=QUERY_N_RESULTS):
    path = (
        f"/api/v2/tenants/{TENANT}/databases/{DATABASE}"
        f"/collections/{COLL_ID}/query"
    )
    body = {
        "query_embeddings": [query_emb],
        "n_results": n_results,
    }
    req = urllib.request.Request(
        CHROMA_BASE + path, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def call_minimax_m3(system_prompt, user_prompt, max_tokens=2048):
    import http.client
    body = json.dumps(
        {
            "model": MINIMAX_MODEL,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    conn = http.client.HTTPSConnection(MINIMAX_HOST, timeout=180)
    conn.request(
        "POST",
        "/anthropic/v1/messages",
        body=body,
        headers={
            "x-api-key": MINIMAX_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    conn.close()
    obj = json.loads(data)
    content = obj.get("content", [])
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "".join(parts)
    return str(content)


def build_style_prompt(examples):
    bullets = []
    for i, e in enumerate(examples, 1):
        title = e.get("title", "")
        doc = (e.get("document") or "").strip()
        if len(doc) > 700:
            doc = doc[:700] + "..."
        bullets.append("--- 样本 " + str(i) + "（标题：" + title + "）---\n" + doc + "\n")
    return "\n".join(bullets)


def main():
    title_hint = sys.argv[1] if len(sys.argv) > 1 else "宏观财经评论"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else QUERY_N_RESULTS
    print("query hint:", title_hint, "n=", n, flush=True)

    emb = embed_query(title_hint)
    print("embed dim:", len(emb), flush=True)

    res = chroma_query(emb, n_results=n)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    if not docs:
        print("no examples, fallback to generic", flush=True)
        examples = []
    else:
        examples = [
            {"title": m.get("title", ""), "document": d}
            for d, m in zip(docs, metas)
        ]
    print("got", len(examples), "examples", flush=True)

    style_block = build_style_prompt(examples) if examples else "（暂无历史文章样本）"

    system_prompt = (
        "你是一个公众号作者，专门把 B 站充电视频的内容改写成公众号文章。"
        "下面给你若干篇你自己过往已发文章片段，你必须学习并复刻这些片段里的真实口吻："
        "用词、句式、情绪、标点、反问/吐槽/类比、开头结尾套路、口头禅等。"
        "总结完后，下次写新文章时严格按这套口吻来。"
    )

    analysis_prompt = (
        "请阅读以下 " + str(len(examples)) + " 篇你自己过往发表过的公众号文章片段，"
        "总结你自己一贯的写作口吻特征。\n\n"
        "要求：\n"
        "1. 列点总结口吻（人称、用词、句式、情绪、标志性句型、是否幽默吐槽），不限字数\n"
        "2. 列出 5-8 个你常用的开头套路和 5-8 个常用结尾套路\n"
        "3. 列出 10-15 个高频口头禅/短语（按出现频次）\n"
        "4. 描述你的文章结构特点（段落长短、是否用列表、是否引经据典）\n"
        "5. 描述你的核心观点/立场\n"
        "6. 不要写'总结如下'这种书面语开头\n\n"
        "【历史文章片段】\n" + style_block
    )

    print("=== calling MiniMax to analyze style ===", flush=True)
    style_summary = call_minimax_m3(system_prompt, analysis_prompt, max_tokens=4096)
    print("\n=== STYLE SUMMARY ===\n" + style_summary, flush=True)

    out = "/vol2/1000/docker_related/gzh-chroma/style_summary.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(style_summary)
    print("\nsaved to " + out, flush=True)


if __name__ == "__main__":
    main()
