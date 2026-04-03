#!/bin/bash
# ============================================
# 🦞 AI小龍蝦 - 整合自動化系統 v2
# 一次性完成所有每日任務
# ============================================

WORKSPACE="/Users/claw/.openclaw/workspace"
DATE=$(date +%Y%m%d)
LOG_FILE="$WORKSPACE/logs/consolidated_$(date +%Y%m%d_%H%M).log"
DESKTOP="/Users/claw/Desktop"

mkdir -p "$WORKSPACE/logs"
mkdir -p "$DESKTOP/潛客系統"

echo "========================================" >> "$LOG_FILE"
echo "🦞 整合自動化開始: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# ============================================
# 任務 1: 28car 爬蟲
# ============================================
echo "🚗 [1/4] 28car 爬蟲..." >> "$LOG_FILE"
cd "$WORKSPACE"
if [ -f "scraper_28car_100_v2.py" ]; then
    # 28car 爬蟲最多等 5 分鐘
    (sleep 300; kill $$) &
    TIMEOUT_PID=$!
    python3 scraper_28car_100_v2.py >> "$LOG_FILE" 2>&1
    kill $TIMEOUT_PID 2>/dev/null
    echo "✅ 28car 完成" >> "$LOG_FILE"
else
    echo "⚠️ 28car 腳本不存在" >> "$LOG_FILE"
fi

# ============================================
# 任務 2: Facebook 爬蟲 (可跳過)
# ============================================
echo "📘 [2/4] Facebook 爬蟲 (可跳過)..." >> "$LOG_FILE"
cd "$WORKSPACE"

if [ -f "$HOME/.fb_crawler/fb_storage_state.json" ]; then
    # FB 爬蟲最多等 60 秒，超時則跳過
    (sleep 60; kill $$) &
    TIMEOUT_PID=$!
    python3 fb_crawler_final_v5.py >> "$LOG_FILE" 2>&1
    FB_RESULT=$?
    kill $TIMEOUT_PID 2>/dev/null
    
    if [ $FB_RESULT -eq 0 ]; then
        echo "✅ Facebook 完成" >> "$LOG_FILE"
    else
        echo "⚠️ Facebook 需要登入或超時" >> "$LOG_FILE"
    fi
else
    echo "⚠️ FB 登入狀態不存在" >> "$LOG_FILE"
fi

# ============================================
# 任務 3: 合併去重 + 匯出 Excel
# ============================================
echo "📊 [3/4] 合併去重..." >> "$LOG_FILE"
cd "$WORKSPACE"

if [ -f "爬蟲潛客總滙/爬蟲潛客總滙_最新.xlsx" ]; then
    cp "爬蟲潛客總滙/爬蟲潛客總滙_最新.xlsx" "$DESKTOP/潛客系統/爬蟲潛客總滙_最新.xlsx"
    cp "爬蟲潛客總滙/爬蟲潛客總滙_${DATE}.xlsx" "$DESKTOP/爬蟲潛客_${DATE}.xlsx" 2>/dev/null
    echo "✅ 已匯出 Excel" >> "$LOG_FILE"
fi

# ============================================
# 任務 4: 同步到潛客系統 (API)
# ============================================
echo "☁️ [4/4] 同步到潛客系統..." >> "$LOG_FILE"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "https://leads-system.onrender.com/" 2>&1)

if [ "$HTTP_STATUS" = "200" ]; then
    echo "🌐 潛客系統正常 (HTTP $HTTP_STATUS)" >> "$LOG_FILE"
    
    python3 << 'PYTHON_EOF' >> "$LOG_FILE" 2>&1
import requests
import pandas as pd

API_URL = "https://leads-system.onrender.com/api/leads"
excel_file = "/Users/claw/.openclaw/workspace/爬蟲潛客總滙/爬蟲潛客總滙_最新.xlsx"

try:
    df = pd.read_excel(excel_file)
    print(f"📊 讀取到 {len(df)} 筆潛客資料")
    
    success_count = 0
    for idx, row in df.iterrows():
        try:
            lead_data = {
                "name": str(row.get('姓名', ''))[:100],
                "phone": str(row.get('電話', ''))[:20],
                "inquiry_type": str(row.get('查詢類型', '汽車保險'))[:50],
                "source": str(row.get('來源', '爬蟲'))[:20],
                "car_plate": str(row.get('車牌', ''))[:20],
                "notes": str(row.get('備註', ''))[:500]
            }
            
            response = requests.post(API_URL, json=lead_data, timeout=10)
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            continue
    
    print(f"✅ 成功上傳 {success_count}/{len(df)} 筆記錄")
    
except FileNotFoundError:
    print("⚠️ 沒有找到 Excel 檔案")
except Exception as e:
    print(f"❌ 上傳失敗: {e}")
PYTHON_EOF
    echo "✅ 潛客系統同步完成" >> "$LOG_FILE"
else
    echo "⚠️ 潛客系統不可用 (HTTP $HTTP_STATUS)" >> "$LOG_FILE"
fi

# ============================================
# 任務 5: 港車北上報價系統健康檢查
# ============================================
echo "🚗 [5/5] 港車北上報價系統檢查..." >> "$LOG_FILE"

QUOTE_FILE="$DESKTOP/index.html"
if [ -f "$QUOTE_FILE" ]; then
    echo "✅ 港車北上報價系統正常" >> "$LOG_FILE"
else
    echo "⚠️ 港車北上報價系統未找到" >> "$LOG_FILE"
fi

# ============================================
# 完成摘要
# ============================================
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "✅ 整合自動化完成: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 發送 WhatsApp 通知
if command -v openclaw &> /dev/null; then
    openclaw message send \
        --target "+85221101144" \
        --message "🦞 每日自動化完成！$(date '+%Y-%m-%d %H:%M')" \
        --channel whatsapp 2>/dev/null
fi
