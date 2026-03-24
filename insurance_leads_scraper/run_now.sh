#!/bin/bash
# 手動執行爬蟲

cd "$(dirname "$0")"

echo "🚀 手動執行整合爬蟲系統..."
echo "開始時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

python3 daily_scraper.py

EXIT_CODE=$?

echo ""
echo "結束時間: $(date '+%Y-%m-%d %H:%M:%S')"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 執行成功"
else
    echo "⚠️ 執行失敗 (退出碼: $EXIT_CODE)"
fi

exit $EXIT_CODE
