#!/bin/bash
# Dcard 熱門 Lite - 爬取 + 推送到 GitHub Pages
set -e
cd "$(dirname "$0")"

echo "1/3 更新 posts.json..."
python3 fetch_dcard.py --limit 30

echo ""
echo "2/3 檢查變更..."
if git diff --quiet posts.json img/ 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard img/)" ]; then
  echo "   無變更，跳過推送"
  exit 0
fi

echo ""
echo "3/3 推送到 GitHub..."
git add posts.json img/
git commit -m "data: $(date '+%Y-%m-%d %H:%M:%S')"
git push 2>&1 | sed 's/ghp_[a-zA-Z0-9]*/ghp_***REDACTED***/g'

echo ""
echo "✅ 完成 https://iwantabbot.github.io/dcard-lite/"
