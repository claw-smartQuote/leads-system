#!/bin/bash
# 檢查 Render 潛客系統新 lead 並發送 WhatsApp 通知

URL="https://leads-system.onrender.com/api/leads"
STATE_FILE="/Users/claw/.openclaw/workspace/.last_lead_count"

# 獲取當前 leads 列表
RESPONSE=$(curl -s --max-time 30 "$URL" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$RESPONSE" ]; then
    echo "$(date): 無法連接到 Render 服務"
    exit 1
fi

# 計算 leads 數量
CURRENT_COUNT=$(echo "$RESPONSE" | grep -o '"id"' | wc -l)

# 讀取上次記錄
LAST_COUNT=0
if [ -f "$STATE_FILE" ]; then
    LAST_COUNT=$(cat "$STATE_FILE")
fi

# 如果有新 leads
if [ "$CURRENT_COUNT" -gt "$LAST_COUNT" ]; then
    NEW_LEADS=$((CURRENT_COUNT - LAST_COUNT))
    echo "$(date): 發現 $NEW_LEADS 個新潛客！"
    
    # 保存新數量
    echo "$CURRENT_COUNT" > "$STATE_FILE"
    
    # 返回新 lead 信息（給調用者處理）
    echo "$RESPONSE" | tail -n $((NEW_LEADS * 10))
    exit 0
else
    # 更新數量（確保一致）
    echo "$CURRENT_COUNT" > "$STATE_FILE"
    exit 1
fi