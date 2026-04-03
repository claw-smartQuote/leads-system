#!/bin/bash
# 檢查潛客系統健康狀態
# 執行時間: 每日早上 9:00

LOG_FILE="/Users/claw/.openclaw/workspace/logs/healthcheck_$(date +%Y%m%d).log"
LEADS_URL="https://leads-system.onrender.com/"

echo "[$(date)] 檢查潛客系統狀態..." >> "$LOG_FILE"

# 檢查網站是否可訪問
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$LEADS_URL" 2>&1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 潛客系統正常運行 (HTTP $HTTP_CODE)" >> "$LOG_FILE"
else
    echo "⚠️ 潠客系統異常 (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    # 發送 WhatsApp 通知
    MESSAGE="⚠️ 潛客系統異常：https://leads-system.onrender.com/ 返回 HTTP $HTTP_CODE，請及時檢查！"
    openclaw message send --target +85260444446 --message "$MESSAGE" 2>&1 >> "$LOG_FILE"
fi

echo "完成: $(date)" >> "$LOG_FILE"
