#!/bin/bash
# 港車北上報價系統健康檢查
# 執行時間: 每日早上 9:00

LOG_FILE="/Users/claw/.openclaw/workspace/logs/quote_health_$(date +%Y%m%d).log"

echo "[$(date)] 港車北上報價系統檢查" >> "$LOG_FILE"

# 港車北上報價系統是本地HTML文件（content:// URI）
# 需要用戶通過 paired node 檢查，或手動確認
# 這裡只是記錄日誌

echo "📱 港車北上報價系統：content://com.zui.filemanager/files/.filemanager/zip_tmp/index.html" >> "$LOG_FILE"
echo "💡 提示：請定期確認本地報價系統可正常打開" >> "$LOG_FILE"
