"""用 playwright 抓每篇公众号文章的正文存成 markdown。"""
import asyncio
import json
import os
import re
import sys
from playwright.async_api import async_playwright


async def fetch_article(page, url, out_dir):
    print(f"fetching {url}", flush=True)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  goto warn: {e}", flush=True)
    await page.wait_for_timeout(3000)

    title = await page.evaluate(
        """() => {
            const el = document.querySelector('#activity-name, .rich_media_title, h1');
            return el ? el.innerText.trim() : document.title;
        }"""
    )
    author = await page.evaluate(
        """() => {
            const el = document.querySelector('#js_name, .rich_media_meta_nickname, .profile_nickname');
            return el ? el.innerText.trim() : '';
        }"""
    )
    publish_time = await page.evaluate(
        """() => {
            const el = document.querySelector('#publish_time, .rich_media_meta_text');
            return el ? el.innerText.trim() : '';
        }"""
    )
    content_html = await page.evaluate(
        """() => {
            const el = document.querySelector('#js_content, .rich_media_content');
            return el ? el.innerHTML : '';
        }"""
    )
    content_text = await page.evaluate(
        """() => {
            const el = document.querySelector('#js_content, .rich_media_content');
            if (!el) return '';
            return el.innerText.trim();
        }"""
    )

    if not content_text or len(content_text) < 50:
        print(f"  skip empty/short: {len(content_text)} chars", flush=True)
        return None

    safe_title = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", title)[:60]
    fname = f"{safe_title}.md"
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        if author:
            f.write(f"> 作者: {author}\n\n")
        if publish_time:
            f.write(f"> 发布时间: {publish_time}\n\n")
        f.write(f"> 原文链接: {url}\n\n")
        f.write("---\n\n")
        f.write(content_text)
        f.write("\n")
    print(f"  saved {fpath} ({len(content_text)} chars)", flush=True)
    return {"title": title, "author": author, "publish_time": publish_time, "url": url, "file": fpath, "length": len(content_text)}


async def main(links_file, out_dir):
    with open(links_file, "r", encoding="utf-8") as f:
        links = json.load(f)
    print(f"{len(links)} links to fetch", flush=True)
    os.makedirs(out_dir, exist_ok=True)

    manifest = []
    async with async_playwright() as p:
        kwargs = dict(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        for cp in [os.environ.get("CHROMIUM_PATH"), "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
            if cp and os.path.exists(cp):
                kwargs["executable_path"] = cp
                print(f"using system chromium: {cp}", flush=True)
                break
        browser = await p.chromium.launch(**kwargs)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()
        for i, item in enumerate(links):
            print(f"\n[{i+1}/{len(links)}]", flush=True)
            try:
                r = await fetch_article(page, item["url"], out_dir)
                if r:
                    manifest.append(r)
            except Exception as e:
                print(f"  fail: {e}", flush=True)
            await page.wait_for_timeout(2000)
        await browser.close()

    manifest_path = os.path.join(out_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n=== {len(manifest)} articles saved ===", flush=True)
    print(f"manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    links = sys.argv[1] if len(sys.argv) > 1 else "/vol2/1000/docker_related/gzh-chroma/sogou_links.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "/vol2/1000/docker_related/gzh-chroma/articles"
    asyncio.run(main(links, out))
