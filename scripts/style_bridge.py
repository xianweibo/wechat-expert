"""沙箱/本地无法直连 NAS 时的"风格总结"桥梁。

用法：
  python3 style_bridge.py articles/*.md > style_summary.txt

输入：
  一堆已经爬下来的 .md 文件 (标题 + 正文)

输出：
  一段基于 MiniMax-M3 的"语言风格"总结，
  格式与 scripts/analyze_style.py 一致，便于直接覆盖
  /vol2/1000/docker_related/gzh-chroma/style_summary.txt
"""

import json
import os
import re
import sys
import glob
import http.client


MINIMAX_HOST = os.environ.get("MINIMAX_HOST", "api.minimaxi.com")
MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
MINIMAX_KEY = os.environ.get("MINIMAX_KEY", "")
MAX_CHARS_PER_SAMPLE = 800
TOP_N = 6


def call_minimax(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    if not MINIMAX_KEY:
        sys.stderr.write("!! MINIMAX_KEY 为空，无法调用 MiniMax\n")
        sys.exit(2)
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
        return "".join(
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        )
    return str(content)


MD_HEAD = re.compile(r"---\s*$", re.M)


def parse_md(path: str):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    title = ""
    lines = text.split("\n")
    for line in lines[:20]:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    m = MD_HEAD.search(text)
    body = text[m.end():].strip() if m else text
    return title, body


def main():
    if len(sys.argv) < 2:
        print("用法: python3 style_bridge.py articles/*.md", file=sys.stderr)
        sys.exit(1)

    files = []
    for arg in sys.argv[1:]:
        files.extend(glob.glob(arg))
    files = sorted({f for f in files if not os.path.basename(f).startswith("_")})
    if not files:
        print("没找到任何 .md 文件", file=sys.stderr)
        sys.exit(1)

    samples = []
    for fp in files[:TOP_N]:
        title, body = parse_md(fp)
        body = body[:MAX_CHARS_PER_SAMPLE]
        samples.append((title, body))
        print(f"-- {fp}: title='{title}' body={len(body)} chars", file=sys.stderr)

    style_block = "\n\n".join(
        f"--- 样本 {i+1}（标题：{t}）---\n{b}" for i, (t, b) in enumerate(samples)
    )

    system_prompt = (
        "你是一个公众号作者，正在给自己复盘'一贯的写作口吻'，"
        "目的是让下次写稿时严格按这个口吻来。"
    )

    user_prompt = (
        f"下面是你过去 {len(samples)} 篇公众号文章片段。"
        f"请总结出你自己一贯的写作口吻特征：\n\n"
        f"1. 用 300 字左右，分点列出口吻（人称、用词、句式节奏、情绪基调、是否幽默/吐槽/反问、典型句型）\n"
        f"2. 给出 3-5 个常用的开头套路，3-5 个常用的结尾套路\n"
        f"3. 列出 5-10 个你高频使用的口头禅/短语\n"
        f"4. 不要再写'总结如下'这种书面语开头，直接进入\n\n"
        f"【历史文章片段】\n{style_block}"
    )

    print(f"=== calling {MINIMAX_MODEL} on {MINIMAX_HOST} ===", file=sys.stderr)
    result = call_minimax(system_prompt, user_prompt, max_tokens=2048)
    print(result)


if __name__ == "__main__":
    main()