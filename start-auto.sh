#!/bin/bash
# 啟動每 5 分鐘自動更新的背景程式
echo "Dcard Lite 自動更新已啟動"
echo "  每 5 分鐘爬取 + 推送"
echo "  日誌: /tmp/dcard-lite.log"
echo "  停止: kill \$(cat /tmp/dcard-lite.pid)"
echo ""
echo "PID: $$"
echo $$ > /tmp/dcard-lite.pid
while true; do
  /Users/agent/dcard-lite/deploy.sh >> /tmp/dcard-lite.log 2>&1
  sleep 300
done
