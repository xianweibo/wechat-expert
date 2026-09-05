import asyncio
import json
import os
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright

BVID = "BV1bZEr6JEDM"


async def main():
    async with async_playwright() as p:
        kwargs = dict(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        for cp in [os.environ.get("CHROMIUM_PATH"), "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
            if cp and os.path.exists(cp):
                kwargs["executable_path"] = cp
                break
        browser = await p.chromium.launch(**kwargs)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        page = await ctx.new_page()
        await page.goto(f"https://www.bilibili.com/video/{BVID}/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        # Extract video metadata + subtitle URL
        data = await page.evaluate(
            """() => {
                const s = window.__INITIAL_STATE__ || {};
                const v = s.videoData || {};
                const out = {
                    title: v.title,
                    desc: v.desc,
                    pubdate: v.pubdate,
                    duration: v.duration,
                    owner: v.owner,
                    stat: v.stat,
                    cid: v.cid,
                    aid: v.aid,
                    bvid: v.bvid,
                };
                const player = s.videoData?.subtitle?.list || s.subtitle?.list || [];
                out.subtitle_list = player;
                return out;
            }"""
        )
        print(json.dumps(data, ensure_ascii=False, indent=2)[:3000], flush=True)

        # Now try to fetch the subtitle using the cid we got
        cid = data.get("cid")
        aid = data.get("aid")
        print(f"cid={cid} aid={aid}", flush=True)
        await browser.close()

        if cid and aid:
            url = f"https://api.bilibili.com/x/v2/subtitle/web/view?oid={cid}&pid={aid}&type=1"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": f"https://www.bilibili.com/video/{BVID}/",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    d = json.loads(r.read().decode("utf-8"))
                    print("\n=== subtitle web view ===", flush=True)
                    print(json.dumps(d, ensure_ascii=False, indent=2)[:3000], flush=True)
            except urllib.error.HTTPError as e:
                print("subtitle HTTP", e.code, e.read().decode("utf-8", errors="replace")[:300])
            except Exception as e:
                print("subtitle ERR", e)


asyncio.run(main())
