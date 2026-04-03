#!/bin/bash
# 每日爬蟲自動化腳本
# 執行時間: 每日早上 8:00
# 任務: 28car + Facebook 爬蟲自動化

WORKSPACE="/Users/claw/.openclaw/workspace"
DATE=$(date +%Y%m%d)
LOG_FILE="$WORKSPACE/logs/scraper_$(date +%Y%m%d_%H%M).log"

# 確保日誌目錄存在
mkdir -p "$WORKSPACE/logs"

echo "========================================" >> "$LOG_FILE"
echo "🦞 每日爬蟲任務開始: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 1. 執行 28car 爬蟲
echo "🚗 執行 28car 爬蟲..." >> "$LOG_FILE"
cd "$WORKSPACE"
python3 scraper_28car_100_v2.py >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"

# 2. Facebook 爬蟲 - 自動化流程
echo "📘 檢查 Facebook 登入狀態..." >> "$LOG_FILE"

if [ -f "$HOME/.fb_crawler/fb_storage_state.json" ]; then
    # 檢查 cookies 是否過期
    COOKIE_AGE=$(stat -f "%Sm" -t "%s" "$HOME/.fb_crawler/fb_storage_state.json" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    AGE_DAYS=$(( (NOW - COOKIE_AGE) / 86400 ))
    
    if [ "$AGE_DAYS" -gt 7 ]; then
        echo "⚠️  Cookies 已过期 ($AGE_DAYS 天)，運行自動登入..." >> "$LOG_FILE"
        python3 fb_auto_login.py >> "$LOG_FILE" 2>&1
    fi
fi

# 執行 Facebook 爬蟲
echo "📘 執行 Facebook 爬蟲..." >> "$LOG_FILE"
python3 fb_crawler_final_v5.py >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"

# 3. 整合爬蟲結果
echo "🔄 整合爬蟲結果..." >> "$LOG_FILE"
if [ -f "$WORKSPACE/merge_scraper_leads.py" ]; then
    python3 merge_scraper_leads.py >> "$LOG_FILE" 2>&1
fi
echo "" >> "$LOG_FILE"

# 4. 複製到桌面潛客系統
echo "📋 複製到桌面潛客系統..." >> "$LOG_FILE"
DESKTOP_DIR="/Users/claw/Desktop/潛客系統"
mkdir -p "$DESKTOP_DIR"

# 查找最新的 Excel 文件
for f in "$WORKSPACE"/fb_潛客_${DATE}*.xlsx "$WORKSPACE"/fb_leads_${DATE}*.xlsx "$WORKSPACE/爬蟲潛客總滙/爬蟲潛客_最新.xlsx"; do
    if [ -f "$f" ]; then
        cp "$f" "$DESKTOP_DIR/爬蟲潛客_${DATE}.xlsx"
        echo "✅ 已複製: $f" >> "$LOG_FILE"
        break
    fi
done

# 同時複製一份到桌面根目錄
if [ -f "$DESKTOP_DIR/爬蟲潛客_${DATE}.xlsx" ]; then
    cp "$DESKTOP_DIR/爬蟲潛客_${DATE}.xlsx" ~/Desktop/fb_潛客_${DATE}.xlsx
    echo "✅ 已複製到桌面: ~/Desktop/fb_潛客_${DATE}.xlsx" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "✅ 任務完成: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 5. 發送 WhatsApp 通知（可選）
# if command -v openclaw &> /dev/null; then
#     openclaw message send --target "+85221101144" --message "🦞 爬蟲完成！"
# fi
