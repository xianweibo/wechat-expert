"""用 playwright + 系统 chromium 渲染搜狗微信搜索，拿到公众号文章链接列表。

跟旧版差别： 用 executable_path 直接调 /usr/bin/chromium，
避免 playwright 拉浏览器二进制卡住。
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright


CHROMIUM_PATHS = [
    os.environ.get("CHROMIUM_PATH"),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]


async def _resolve_chromium():
    for p in CHROMIUM_PATHS:
        if p and os.path.exists(p):
            return p
    return None


async def search_sogou(query: str, pages: int = 3, headless: bool = True):
    exe = await _resolve_chromium()
    results = []
    async with async_playwright() as p:
        kwargs = dict(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        if exe:
            kwargs["executable_path"] = exe
            print(f"using system chromium: {exe}", flush=True)
        else:
            print("using bundled chromium (playwright will download if missing)", flush=True)
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

        for page_idx in range(1, pages + 1):
            url = (
                f"https://weixin.sogou.com/weixin?type=2&query={query}"
                f"&ie=utf8&page={page_idx}"
            )
            print(f"[page {page_idx}] GET {url}", flush=True)
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"  goto warn: {e}", flush=True)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e2:
                    print(f"  goto fail: {e2}", flush=True)
                    continue

            await page.wait_for_timeout(2000)

            anchors = await page.query_selector_all("a[uigs-l]")
            print(f"  found {len(anchors)} result links", flush=True)

            for a in anchors:
                href = await a.get_attribute("href")
                title_el = await a.query_selector("em, .tit, .wx-rb-vic")
                title = ""
                if title_el:
                    title = (await title_el.inner_text()).strip()
                if not title:
                    title = (await a.inner_text()).strip()
                if href and "mp.weixin.qq.com" in (href or ""):
                    results.append({"title": title, "url": href})
                else:
                    if href:
                        real = await page.evaluate(
                            """async (h) => {
                                try {
                                    const r = await fetch(h, {redirect: 'follow', credentials: 'include'});
                                    return r.url;
                                } catch (e) { return null; }
                            }""",
                            href,
                        )
                        if real and "mp.weixin.qq.com" in real:
                            results.append({"title": title, "url": real})

            await page.wait_for_timeout(2500)

        await browser.close()

    seen = set()
    unique = []
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        unique.append(r)
    return unique


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "小喇叭大只讲"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    out = sys.argv[3] if len(sys.argv) > 3 else "/vol2/1000/docker_related/gzh-chroma/sogou_links.json"
    res = asyncio.run(search_sogou(q, pages))
    print(f"\n=== {len(res)} unique mp.weixin.qq.com links ===", flush=True)
    for r in res:
        print(f"- {r['title']}\n  {r['url']}", flush=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"\nsaved to {out}", flush=True)
