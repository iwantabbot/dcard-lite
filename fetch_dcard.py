#!/usr/bin/env python3
"""
Dcard 熱門文章爬蟲 (Playwright + Chrome)
透過真實瀏覽器繞過 Cloudflare，產出 posts.json 靜態快取

用法:
  python3 fetch_dcard.py              # 一次性 (預設含內文留言)
  python3 fetch_dcard.py --daemon     # 常駐模式
  python3 fetch_dcard.py --fast       # 只爬列表 (不含內文，較快)

cron 範例 (每5分鐘):
  */5 * * * * cd /path/to/dcard-lite && python3 fetch_dcard.py 2>>cron.log

依賴:
  pip install playwright
  python3 -m playwright install chromium
  (需要系統安裝 Google Chrome)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent
POSTS_FILE = DATA_DIR / "posts.json"
API = "https://www.dcard.tw/service/api/v2"
CST = timezone(timedelta(hours=8))


def _launch_browser():
    """啟動真實瀏覽器 (系統 Chrome 優先)"""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    # 嘗試系統 Chrome > Playwright Chromium
    try:
        browser = pw.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
    except Exception:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="zh-TW",
    )
    page = ctx.new_page()
    page.add_init_script(
        'Object.defineProperty(navigator, "webdriver", {get: () => false})'
    )
    return pw, browser, page


def _warm_up(page):
    """先拜訪首頁讓 Cloudflare 設定 cookie"""
    page.goto("https://www.dcard.tw/f", wait_until="domcontentloaded", timeout=30000)
    # 等 Cloudflare challenge 通過 (最多10秒)
    for _ in range(20):
        time.sleep(0.5)
        if "Cloudflare" not in page.title() and "Attention" not in page.title():
            break


def _browser_fetch(page, url):
    """在瀏覽器內 fetch API"""
    js = f"""async () => {{
        const r = await fetch("{url}");
        if (!r.ok) return null;
        return await r.json();
    }}"""
    try:
        return page.evaluate(js)
    except Exception:
        return None


def _close(pw, browser):
    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


def simplify(p):
    media = p.get("media", [])
    return {
        "id": p.get("id"),
        "title": p.get("title", ""),
        "excerpt": p.get("excerpt", ""),
        "forumAlias": p.get("forumAlias", ""),
        "forumName": p.get("forumName", ""),
        "likeCount": p.get("likeCount", 0),
        "commentCount": p.get("commentCount", 0),
        "thumbnail": media[0].get("url") if media else None,
        "createdAt": p.get("createdAt", ""),
    }


def run(limit=30, details=False):
    now = datetime.now(CST)
    print(f"[{now:%Y-%m-%d %H:%M:%S}] 啟動 Chrome 爬取 Dcard 熱門...")

    pw, browser, page = _launch_browser()
    try:
        print("  連線 dcard.tw (等待 Cloudflare)...")
        _warm_up(page)

        # 取得熱門文章列表
        raw = _browser_fetch(page, f"{API}/posts?popular=true&limit={limit}")
        if not raw:
            print("[FAIL] API 回傳為空")
            return False

        posts = [simplify(p) for p in raw]
        print(f"  取得 {len(posts)} 篇文章")

        # 選擇性爬內文與留言
        if details:
            for i, post in enumerate(posts):
                pid = post["id"]
                d = _browser_fetch(page, f"{API}/posts/{pid}")
                if d:
                    post["content"] = d.get("content", "")
                c = _browser_fetch(page, f"{API}/posts/{pid}/comments?limit=30")
                if c:
                    post["comments"] = [
                        {"floor": x.get("floor"), "content": x.get("content", ""),
                         "likeCount": x.get("likeCount", 0)}
                        for x in c
                    ]
                if (i + 1) % 5 == 0:
                    print(f"  內文 {i+1}/{len(posts)}")
                time.sleep(0.3)

        # 寫入 JSON
        out = {"fetchedAt": now.isoformat(), "count": len(posts), "posts": posts}
        POSTS_FILE.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  -> posts.json ({POSTS_FILE.stat().st_size:,} bytes)")
        return True

    finally:
        _close(pw, browser)


def main():
    ap = argparse.ArgumentParser(description="Dcard 熱門爬蟲 (Chrome)")
    ap.add_argument("--limit", type=int, default=30, help="文章數量 (預設30)")
    ap.add_argument("--fast", action="store_true", help="只爬列表，不含內文留言")
    ap.add_argument("--daemon", action="store_true", help="常駐模式")
    ap.add_argument("--interval", type=int, default=300, help="爬取間隔秒 (預設300)")
    args = ap.parse_args()

    if args.daemon:
        print(f"常駐模式: 每 {args.interval}s")
        while True:
            try:
                run(limit=args.limit, details=not args.fast)
            except Exception as e:
                print(f"[ERROR] {e}")
            time.sleep(args.interval)
    else:
        ok = run(limit=args.limit, details=not args.fast)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
