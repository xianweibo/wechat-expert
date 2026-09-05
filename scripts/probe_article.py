"""拉取一篇已知公众号文章，找出真实的 MP 名字。"""
import asyncio
import os
import sys
import urllib.parse
from playwright.async_api import async_playwright


URL = "http://mp.weixin.qq.com/s?__biz=MzU0MzU1ODI3MA==&mid=2247483975&idx=1&sn=7d157bf9076cbcaca5bbd28004f79d40&chksm=fb08dd56cc7f5440fe8919bd163644eea6f15b9751d6ff023cd7b7fc2fc5ee3639b7f3b2ea19#rd"


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
        print(f"GET {URL}", flush=True)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"goto warn: {e}", flush=True)
        await page.wait_for_timeout(4000)
        title = await page.title()
        print(f"title: {title}", flush=True)
        mp_name = await page.evaluate(
            "() => { const el = document.querySelector('#js_name, .rich_media_meta_nickname, .profile_nickname'); return el ? el.innerText.trim() : ''; }"
        )
        print(f"mp_name: {mp_name!r}", flush=True)
        article_title = await page.evaluate(
            "() => { const el = document.querySelector('#activity-name, .rich_media_title, h1'); return el ? el.innerText.trim() : ''; }"
        )
        print(f"article_title: {article_title!r}", flush=True)
        biz = await page.evaluate(
            "() => { const m = location.href.match(/__biz=([^&]+)/); return m ? m[1] : ''; }"
        )
        print(f"__biz: {biz!r}", flush=True)
        await browser.close()


asyncio.run(main())
