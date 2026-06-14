#!/usr/bin/env python3
"""Cover image generation via MiniMax image_generation API.

Usage:
  python3 cover_gen.py "标题" ["摘要" ] [output_path] [--model image-01] [--aspect 16:9]

Env vars:
  MINIMAX_API_KEY         MiniMax API key (必填)
  MINIMAX_IMAGE_MODEL     默认 image-01
  MINIMAX_HOST            默认 api.minimaxi.com
  COVER_ASPECT_RATIO      默认 16:9
  COVERS_DIR              默认 ./covers
"""
import argparse
import base64
import http.client
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


def call_image_gen(prompt: str, model: str, aspect_ratio: str, host: str, api_key: str, timeout: int = 120) -> dict:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "n": 1,
            "response_format": "b64_json",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    conn.request(
        "POST",
        "/v1/image_generation",
        body=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "x-api-key": api_key,
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    resp = conn.getresponse()
    data = resp.read().decode("utf-8")
    conn.close()
    if resp.status < 200 or resp.status >= 300:
        raise RuntimeError(f"minimax HTTP {resp.status}: {data[:500]}")
    return json.loads(data)


def build_prompt(title: str, description: str = "", style: str = "") -> str:
    style = style or (
        "modern professional editorial, suitable for Chinese WeChat "
        "public account business content, clean composition, soft natural "
        "lighting, subtle palette"
    )
    desc_part = f"\n\nArticle summary: {description}" if description else ""
    return (
        "Generate a cover image for a Chinese WeChat public account article.\n"
        f"Title: {title}{desc_part}\n\n"
        f"Style: {style}.\n"
        "No text, no logos, no watermarks, no people faces in the foreground."
    )


def extract_image(obj: dict) -> tuple[bytes, str, str]:
    """Return (image_bytes, mime, source_label)."""
    candidates = [
        obj.get("data", {}).get("image_base64") if isinstance(obj.get("data"), dict) else None,
        obj.get("image_base64"),
    ]
    data_list = obj.get("data") if isinstance(obj.get("data"), list) else None
    if data_list:
        for item in data_list:
            if isinstance(item, dict):
                candidates.append(item.get("image_base64") or item.get("b64_json"))

    for c in candidates:
        if isinstance(c, str) and len(c) > 200:
            return base64.b64decode(c), "image/jpeg", "b64_json"

    if data_list and isinstance(data_list, list):
        for item in data_list:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                url = item["url"]
                return _download(url), "image/png" if url.lower().endswith(".png") else "image/jpeg", f"url:{url[:60]}"
    if isinstance(obj.get("data", {}).get("image_url"), str):
        url = obj["data"]["image_url"]
        return _download(url), "image/png" if url.lower().endswith(".png") else "image/jpeg", f"url:{url[:60]}"

    raise RuntimeError(f"no image data in response: {json.dumps(obj)[:500]}")


def _download(url: str) -> bytes:
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fa5_-]", "_", s)
    return s[:60] or "cover"


def generate_cover(
    title: str,
    description: str = "",
    out_path: str | None = None,
    model: str | None = None,
    aspect_ratio: str | None = None,
    covers_dir: str | None = None,
    style: str = "",
) -> dict:
    api_key = os.environ.get("MINIMAX_IMAGE_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY (or MINIMAX_IMAGE_API_KEY) is not set")
    host = os.environ.get("MINIMAX_HOST", "api.minimaxi.com")
    model = model or os.environ.get("MINIMAX_IMAGE_MODEL", "image-01")
    aspect_ratio = aspect_ratio or os.environ.get("COVER_ASPECT_RATIO", "16:9")
    covers_dir = covers_dir or os.environ.get("COVERS_DIR") or str(Path.cwd() / "covers")

    prompt = build_prompt(title, description, style)
    obj = call_image_gen(prompt, model, aspect_ratio, host, api_key)
    data, mime, source = extract_image(obj)

    Path(covers_dir).mkdir(parents=True, exist_ok=True)
    if not out_path:
        ext = "png" if mime == "image/png" else "jpg"
        out_path = str(Path(covers_dir) / f"{safe_filename(title)}_{int(time.time())}.{ext}")
    Path(out_path).write_bytes(data)
    return {
        "ok": True,
        "file_path": out_path,
        "size": len(data),
        "mime": mime,
        "model": model,
        "source": source,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("title")
    p.add_argument("description", nargs="?", default="")
    p.add_argument("out_path", nargs="?", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--aspect", dest="aspect_ratio", default=None)
    p.add_argument("--covers-dir", dest="covers_dir", default=None)
    p.add_argument("--style", default="")
    args = p.parse_args()

    result = generate_cover(
        args.title,
        args.description,
        args.out_path,
        args.model,
        args.aspect_ratio,
        args.covers_dir,
        args.style,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
