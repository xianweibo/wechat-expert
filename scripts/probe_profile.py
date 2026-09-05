"""拉取公众号的公开主页，提取所有文章链接。"""
import asyncio
import json
import os
import re
import sys
import urllib.parse
from playwright.async_api import async_playwright


BIZ = "MzU0MzU1ODI3MA=="


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
        url = f"https://mp.weixin.qq.com/profile?__biz={BIZ}"
        print(f"GET {url}", flush=True)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"goto warn: {e}", flush=True)
        await page.wait_for_timeout(5000)
        title = await page.title()
        print(f"title: {title}", flush=True)
        body = await page.evaluate("() => document.body.innerText.substring(0, 1000)")
        print(f"body[:1000]:", flush=True)
        print(body, flush=True)
        print("---", flush=True)
        # 看 var msgList 之类的内嵌数据
        var_data = await page.evaluate(
            "() => { const out = []; for (const k of Object.keys(window)) { if (/msg|article|list|post|news/i.test(k)) { try { const v = window[k]; if (typeof v === 'string' && v.length > 50) out.push(k + '=' + v.substring(0, 200)); else if (typeof v === 'object') out.push(k + '=' + JSON.stringify(v).substring(0, 200)); } catch(e){} } } return out.slice(0, 30); }"
        )
        print(f"window globals with msg/article/list:", flush=True)
        for x in var_data:
            print(" ", x, flush=True)
        # 看 page 源码
        html = await page.content()
        with open("/tmp/profile.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"saved html {len(html)} bytes", flush=True)
        # 看看有没有现成的 article 链接
        links = await page.evaluate(
            "() => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && h.includes('mp.weixin.qq.com/s'))"
        )
        print(f"article links on profile page: {len(links)}", flush=True)
        for l in links[:20]:
            print(f"  {l}", flush=True)
        await browser.close()


asyncio.run(main())
