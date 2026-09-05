"""Debug: 看 sogou 返回什么内容。"""
import asyncio
import os
from playwright.async_api import async_playwright


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
        url = "https://weixin.sogou.com/weixin?type=2&query=%E5%B0%8F%E6%8C%99%E5%8F%A3%E5%A4%A7%E5%8F%AA%E8%AE%B2&ie=utf8&page=1"
        print(f"GET {url}", flush=True)
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"goto warn: {e}", flush=True)
        await page.wait_for_timeout(3000)
        title = await page.title()
        print(f"title: {title}", flush=True)
        body_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
        print(f"body (first 500 chars):", flush=True)
        print(body_text, flush=True)
        print("---", flush=True)
        anchors_count = await page.evaluate("() => document.querySelectorAll('a').length")
        print(f"a tags: {anchors_count}", flush=True)
        with open("/tmp/sogou_debug.html", "w", encoding="utf-8") as f:
            html = await page.content()
            f.write(html)
        print(f"saved html to /tmp/sogou_debug.html ({len(html)} bytes)", flush=True)
        await browser.close()


asyncio.run(main())
