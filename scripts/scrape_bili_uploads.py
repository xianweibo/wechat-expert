import asyncio
import os
import urllib.parse
from playwright.async_api import async_playwright

UID = 290663424
UPLOADS_URL = f"https://space.bilibili.com/{UID}/upload/video"


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
        for url in [
            UPLOADS_URL,
            f"https://space.bilibili.com/{UID}/upload",
            f"https://space.bilibili.com/{UID}/video",
        ]:
            print(f"=== {url} ===", flush=True)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print("goto err:", e, flush=True)
                continue
            await page.wait_for_timeout(5000)
            title = await page.title()
            print("title:", title, flush=True)
            videos = await page.evaluate(
                """() => Array.from(document.querySelectorAll('a[href*="video/BV"], li .title, .upload-video-card')).slice(0, 30).map(a => {
                    const title = a.querySelector('.title, .bili-video-card__title') || a;
                    const time = a.querySelector('.time, .bili-video-card__stats > span:first-child, .date') || a;
                    return {
                        href: a.href || a.querySelector('a')?.href,
                        title: (title.innerText || '').trim().substring(0, 100),
                        time: (time.innerText || '').trim(),
                    };
                }).filter(x => x.href)"""
            )
            print("videos:", flush=True)
            for v in videos[:20]:
                print(" ", v, flush=True)
            print(flush=True)


asyncio.run(main())
