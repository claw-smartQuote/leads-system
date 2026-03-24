#!/bin/bash
# Render 潛客檢查器 - 發現新 lead 時通知

cd /Users/claw/.openclaw/workspace

# 運行檢查腳本
OUTPUT=$(./check_render_leads.sh 2>&1)
EXIT_CODE=$?

# 如果有新 lead
if [ $EXIT_CODE -eq 0 ]; then
    # 提取最新 lead 信息
    LEAD_INFO=$(echo "$OUTPUT" | grep -A 20 '"id":')
    
    # 提取字段
    NAME=$(echo "$LEAD_INFO" | grep '"name"' | sed 's/.*"name":"\([^"]*\)".*/\1/')
    PHONE=$(echo "$LEAD_INFO" | grep '"phone"' | sed 's/.*"phone":"\([^"]*\)".*/\1/')
    CAR_PLATE=$(echo "$LEAD_INFO" | grep '"car_plate"' | sed 's/.*"car_plate":"\([^"]*\)".*/\1/')
    CAR_MODEL=$(echo "$LEAD_INFO" | grep '"car_model"' | sed 's/.*"car_model":"\([^"]*\)".*/\1/')
    INQUIRY=$(echo "$LEAD_INFO" | grep '"inquiry_type"' | sed 's/.*"inquiry_type":"\([^"]*\)".*/\1/')
    NOTES=$(echo "$LEAD_INFO" | grep '"notes"' | sed 's/.*"notes":"\([^"]*\)".*/\1/' | head -1)
    
    # 創建通知消息
    cat > /tmp/new_lead_notification.txt << EOF
🚗 *新潛客通知 (Render)*

👤 姓名: ${NAME:-N/A}
📱 電話: ${PHONE:-N/A}

🚙 車輛資料:
• 車牌: ${CAR_PLATE:-N/A}
• 型號: ${CAR_MODEL:-N/A}

📋 查詢類型: ${INQUIRY:-N/A}
📝 備註: ${NOTES:-無}

⏰ 檢測時間: $(date '+%Y-%m-%d %H:%M')

👉 請回覆跟進此客戶
EOF

    # 發送到 WhatsApp（通過 OpenClaw 系統）
    MESSAGE=$(cat /tmp/new_lead_notification.txt)
    
    # 記錄到文件，由 OpenClaw 處理
    echo "$MESSAGE" > "/Users/claw/.openclaw/workspace/.pending_whatsapp_notification"
    echo "$(date): 新 lead 通知已準備"
fi