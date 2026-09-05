import asyncio
import json
import os
from playwright.async_api import async_playwright

BVID = "BV1bZEr6JEDM"
URL = f"https://www.bilibili.com/video/{BVID}/"


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
        # collect network calls
        subtitle_urls = []

        def on_request(req):
            if "subtitle" in req.url.lower() or "sub" in req.url.lower():
                subtitle_urls.append(req.url)

        page.on("request", on_request)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print("goto err:", e, flush=True)
        await page.wait_for_timeout(8000)
        try:
            await page.evaluate("window.scrollTo(0, 600)")
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        title = await page.title()
        print("title:", title, flush=True)

        # check window for player state
        player_state = await page.evaluate(
            """() => {
                const out = {};
                for (const k of Object.keys(window)) {
                    if (/^(__INITIAL_STATE__|__playinfo__|__PGC_USERSTATE__|bilibiliPlayer|__BILI_VIDEO_CONFIG__|window\.__INITIAL|__INITIAL__|__NEXT_DATA__)/i.test(k)) {
                        try {
                            const v = window[k];
                            if (typeof v === 'object') {
                                out[k] = JSON.stringify(v).substring(0, 500);
                            } else {
                                out[k] = String(v).substring(0, 500);
                            }
                        } catch(e) {}
                    }
                }
                return out;
            }"""
        )
        for k, v in player_state.items():
            print(f"=== {k} ===", flush=True)
            print(v[:600], flush=True)

        print("subtitle urls seen:", subtitle_urls, flush=True)
        await browser.close()


asyncio.run(main())
