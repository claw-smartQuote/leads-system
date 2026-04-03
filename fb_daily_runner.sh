#!/bin/bash
# FB爬蟲自動化執行腳本
# 任務: 每日自動執行FB爬蟲並匯出Excel

set -e

WORKSPACE="/Users/claw/.openclaw/workspace"
DATE=$(date +%Y%m%d)
LOG_FILE="$WORKSPACE/logs/fb_crawler_$(date +%Y%m%d).log"

# 創建日誌目錄
mkdir -p "$WORKSPACE/logs"

echo "[$(date)] 🚀 開始執行FB爬蟲..." | tee -a "$LOG_FILE"

# 1. 檢查登入狀態並執行爬蟲
cd "$WORKSPACE"

# 檢查是否需要登入
if python3 fb_crawler_final_v5.py --check-login 2>&1 | grep -q "need_login"; then
    echo "[$(date)] 🔐 登入狀態過期，運行自動登入..." | tee -a "$LOG_FILE"
    python3 fb_auto_login.py >> "$LOG_FILE" 2>&1
fi

# 2. 執行爬蟲
echo "[$(date)] 🕷️ 執行爬蟲..." | tee -a "$LOG_FILE"
python3 fb_crawler_final_v5.py >> "$LOG_FILE" 2>&1

# 3. 檢查並匯出Excel到桌面
EXCEL_FILE="$WORKSPACE/fb_潛客_${DATE}.xlsx"
if [ -f "$EXCEL_FILE" ]; then
    cp "$EXCEL_FILE" ~/Desktop/
    echo "[$(date)] ✅ Excel已匯出到桌面: $EXCEL_FILE" | tee -a "$LOG_FILE"
else
    # 嘗試備用文件名
    EXCEL_FILE="$WORKSPACE/fb_leads_${DATE}.xlsx"
    if [ -f "$EXCEL_FILE" ]; then
        cp "$EXCEL_FILE" ~/Desktop/
        echo "[$(date)] ✅ Excel已匯出到桌面: $EXCEL_FILE" | tee -a "$LOG_FILE"
    else
        echo "[$(date)] ⚠️ 未找到Excel文件" | tee -a "$LOG_FILE"
    fi
fi

echo "[$(date)] 🎉 FB爬蟲任務完成！" | tee -a "$LOG_FILE"
