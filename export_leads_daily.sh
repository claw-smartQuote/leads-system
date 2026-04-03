#!/bin/bash
# 潛客系統自動滙出腳本 (已優化版本)
# 每天自動從 Render 後台滙出 Excel 並以日期命名
#
# 修復內容:
# 1. 增加 curl 超時時間到 120 秒
# 2. 添加最多 3 次的重試機制
# 3. 添加詳細的錯誤日誌

set -o pipefail

# 設置
EXPORT_URL="https://leads-system.onrender.com/api/export"
OUTPUT_DIR="/Users/claw/Desktop/潛客系統"
LOG_DIR="/Users/claw/.openclaw/workspace/logs"
DATE_STR=$(date +"%Y-%m-%d")
TIME_STR=$(date +"%H%M")
OUTPUT_FILE="${OUTPUT_DIR}/雲端_render資料_${DATE_STR}.xlsx"
LOG_FILE="${LOG_DIR}/export_leads_${DATE_STR}.log"

# 配置
MAX_RETRIES=3
CURL_TIMEOUT=120
RETRY_DELAY=5

# 確保日誌目錄存在
mkdir -p "${LOG_DIR}"
mkdir -p "${OUTPUT_DIR}"

# 日誌函數
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# 下載函數（帶重試）
download_with_retry() {
    local url="$1"
    local output="$2"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        log_message "INFO" "開始下載 (嘗試 ${attempt}/${MAX_RETRIES}): ${url}"
        
        # 使用 curl 下載，設置超時和重試
        if curl -s --max-time ${CURL_TIMEOUT} \
                  --connect-timeout 30 \
                  --retry 2 \
                  --retry-delay 3 \
                  --retry-max-time 60 \
                  -L \
                  -o "${output}" \
                  "${url}" 2>>"${LOG_FILE}"; then
            
            # 檢查文件是否為有效 Excel
            if file "${output}" | grep -q "Excel\|Microsoft\|Composite Document"; then
                local file_size=$(stat -f%z "${output}" 2>/dev/null || stat -c%s "${output}" 2>/dev/null)
                log_message "INFO" "✅ 下載成功: ${output} (${file_size} bytes)"
                return 0
            else
                log_message "ERROR" "❌ 下載的文件不是有效的 Excel 格式"
                file "${output}" >> "${LOG_FILE}"
                rm -f "${output}"
            fi
        else
            local exit_code=$?
            log_message "ERROR" "❌ 下載失敗 (退出碼: ${exit_code})"
        fi
        
        # 如果不是最後一次嘗試，等待後重試
        if [ $attempt -lt $MAX_RETRIES ]; then
            log_message "INFO" "等待 ${RETRY_DELAY} 秒後重試..."
            sleep ${RETRY_DELAY}
        fi
        
        attempt=$((attempt + 1))
    done
    
    log_message "ERROR" "❌ 所有重試都失敗了"
    return 1
}

# 主程序
main() {
    log_message "INFO" "========================================"
    log_message "INFO" "🦞 潛客系統自動滙出開始"
    log_message "INFO" "========================================"
    log_message "INFO" "輸出文件: ${OUTPUT_FILE}"
    log_message "INFO" "超時設置: ${CURL_TIMEOUT} 秒"
    log_message "INFO" "最大重試: ${MAX_RETRIES} 次"
    
    # 執行下載
    if download_with_retry "${EXPORT_URL}" "${OUTPUT_FILE}"; then
        # 檢查文件大小
        FILE_SIZE=$(stat -f%z "${OUTPUT_FILE}" 2>/dev/null || stat -c%s "${OUTPUT_FILE}" 2>/dev/null)
        
        if [ "$FILE_SIZE" -lt 1000 ]; then
            log_message "WARN" "⚠️  警告: 文件可能為空或無數據 (${FILE_SIZE} bytes)"
        else
            log_message "INFO" "📊 文件大小: $(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')"
        fi
        
        # 清理舊文件（保留最近 30 天的文件）
        log_message "INFO" "清理舊文件..."
        find "${OUTPUT_DIR}" -name "雲端_render資料_*.xlsx" -mtime +30 -delete 2>/dev/null && \
            log_message "INFO" "✅ 已清理 30 天前的舊文件" || \
            log_message "WARN" "⚠️  清理舊文件時出錯（可能沒有舊文件）"
        
        log_message "INFO" "========================================"
        log_message "INFO" "✅ 滙出完成"
        log_message "INFO" "========================================"
        exit 0
    else
        log_message "ERROR" "========================================"
        log_message "ERROR" "❌ 滙出失敗"
        log_message "ERROR" "========================================"
        exit 1
    fi
}

# 執行主程序
main "$@"
