import asyncio
import os
import urllib.parse
from playwright.async_api import async_playwright

UID = 290663424
URL = f"https://space.bilibili.com/{UID}/"


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
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        title = await page.title()
        print("title:", title, flush=True)
        body = await page.evaluate("() => document.body.innerText.substring(0, 800)")
        print("body[:800]:", flush=True)
        print(body, flush=True)
        print("---", flush=True)
        videos = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href*="video/BV"]')).slice(0, 10).map(a => ({
                href: a.href,
                title: a.innerText.trim().substring(0, 100),
                time: a.getAttribute('title') || ''
            }))"""
        )
        print("videos:", flush=True)
        for v in videos:
            print(" ", v, flush=True)
        await browser.close()


asyncio.run(main())
