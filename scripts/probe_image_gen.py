"""探测 MiniMax image-01-live 图像生成 API。"""
import json
import os
import sys
import urllib.request

API_KEY = os.environ.get(
    "MINIMAX_API_KEY",
    os.environ.get('MINIMAX_API_KEY', ''),
)

# MiniMax image generation endpoints
ENDPOINTS = [
    "https://api.minimaxi.com/v1/image_generation",
    "https://api.minimaxi.com/v1/images/generations",
]

MODELS = ["image-01-live", "image-01"]

prompt = "A hand-drawn cartoon style image of a confident Chinese businessman standing at a shareholder meeting podium, with a glowing electric car behind him, 4nm chip floating in air, a green stock chart going up. Exaggerated comic-book style, vibrant warm colors, 16:9 aspect ratio."

for ep in ENDPOINTS:
    for m in MODELS:
        body = {"model": m, "prompt": prompt, "aspect_ratio": "16:9", "n": 1}
        body_alt = {"model": m, "prompt": prompt, "width": 1536, "height": 864, "n": 1}
        for payload in (body, body_alt):
            req = urllib.request.Request(
                ep,
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": "Bearer " + API_KEY,
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    resp = json.loads(r.read().decode("utf-8"))
                    print("OK", ep, m, str(payload.keys()), "->", str(resp)[:500], flush=True)
            except urllib.error.HTTPError as e:
                body_txt = e.read().decode("utf-8", errors="replace")[:300]
                print("HTTP", e.code, ep, m, str(payload.keys()), "->", body_txt, flush=True)
            except Exception as e:
                print("ERR", ep, m, str(payload.keys()), "->", str(e)[:200], flush=True)
