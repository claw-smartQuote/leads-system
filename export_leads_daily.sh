#!/bin/bash
# 潛客系統自動滙出腳本
# 每天自動從 Render 後台滙出 Excel 並以日期命名

# 設置
EXPORT_URL="https://leads-system.onrender.com/api/export"
OUTPUT_DIR="/Users/claw/Desktop/潛客系統"
DATE_STR=$(date +"%Y-%m-%d")
TIME_STR=$(date +"%H%M")
OUTPUT_FILE="${OUTPUT_DIR}/雲端_render資料_${DATE_STR}.xlsx"

# 確保輸出目錄存在
mkdir -p "${OUTPUT_DIR}"

# 下載 Excel 文件
echo "$(date '+%Y-%m-%d %H:%M:%S') - 開始滙出潛客資料..."

if curl -s --max-time 60 "${EXPORT_URL}" -o "${OUTPUT_FILE}"; then
    # 檢查文件是否為有效 Excel
    if file "${OUTPUT_FILE}" | grep -q "Excel"; then
        echo "✅ 滙出成功: ${OUTPUT_FILE}"
        echo "📊 文件大小: $(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')"
        
        # 檢查是否有數據
        FILE_SIZE=$(stat -f%z "${OUTPUT_FILE}" 2>/dev/null || stat -c%s "${OUTPUT_FILE}" 2>/dev/null)
        if [ "$FILE_SIZE" -lt 1000 ]; then
            echo "⚠️  警告: 文件可能為空或無數據"
        fi
    else
        echo "❌ 錯誤: 下載的文件不是有效的 Excel"
        rm -f "${OUTPUT_FILE}"
        exit 1
    fi
else
    echo "❌ 錯誤: 無法連接到後台或下載失敗"
    exit 1
fi

# 清理舊文件（保留最近 30 天的文件）
find "${OUTPUT_DIR}" -name "雲端_render資料_*.xlsx" -mtime +30 -delete 2>/dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') - 滙出完成"
exit 0