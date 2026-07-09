#!/bin/bash
# Dcard 熱門 Lite - 一鍵更新 + 部署
# 用法: ./deploy.sh

set -e
cd "$(dirname "$0")"

echo "1/3 更新 posts.json..."
python3 fetch_dcard.py --limit 30

echo ""
echo "2/3 打包 zip..."
rm -f dcard-lite.zip
zip -j dcard-lite.zip index.html posts.json

echo ""
echo "3/3 部署到 Netlify Drop..."
python3 - <<'PYEOF'
import time
from playwright.sync_api import sync_playwright
from pathlib import Path

SITE_DIR = Path(__file__).parent if "__file__" in dir() else Path(".")
ZIP = SITE_DIR / "dcard-lite.zip"

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome", headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("https://app.netlify.com/drop", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    inp = page.query_selector('input[type="file"]')
    inp.set_input_files(str(ZIP))
    time.sleep(6)

    # Extract URL from page
    body = page.inner_text("body")
    import re
    urls = re.findall(r'https://[\w-]+\.netlify\.app', body)
    if urls:
        print(f"\n✅ 部署完成!")
        print(f"   網址: {urls[0]}")
    else:
        print("\n⚠️  部署完成，但無法自動提取網址")
        print("   請手動到 https://app.netlify.com/drop 查看")

    browser.close()
PYEOF
