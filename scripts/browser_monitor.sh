#!/bin/bash
# 瀏覽器監控腳本 - 監控 Facebook 和 28Car

CDP_URL="http://127.0.0.1:9222"
LOG_FILE="/tmp/browser_monitor.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 啟動瀏覽器監控..." | tee -a "$LOG_FILE"

# 獲取所有分頁信息
get_tabs() {
    curl -s "$CDP_URL/json/list" 2>/dev/null | jq -r '.[] | "\(.id)|\(.url)|\(.title)"' 2>/dev/null
}

# 獲取頁面內容摘要
get_page_summary() {
    local tab_id=$1
    local url=$2
    
    echo "[$tab_id] $url"
    
    # 獲取頁面標題
    curl -s -X POST "$CDP_URL/json/activate/$tab_id" > /dev/null 2>&1
    
    case "$url" in
        *28car.com*)
            echo "  - 這是 28Car 二手車網站"
            echo "  - 可以監控：新車上架、價格變動、搜索結果"
            ;;
        *facebook.com*)
            echo "  - 這是 Facebook"
            echo "  - 可以監控：通知數量、新消息、動態更新"
            ;;
    esac
}

# 主監控循環
while true; do
    echo ""
    echo "===== [$(date '+%Y-%m-%d %H:%M:%S')] 監控報告 ====="
    
    tabs=$(get_tabs)
    
    if [ -z "$tabs" ]; then
        echo "⚠️ 無法連接到 Chrome 調試端口"
        sleep 30
        continue
    fi
    
    # 監控 Facebook
    fb_tab=$(echo "$tabs" | grep "facebook.com" | head -1)
    if [ -n "$fb_tab" ]; then
        fb_id=$(echo "$fb_tab" | cut -d'|' -f1)
        fb_url=$(echo "$fb_tab" | cut -d'|' -f2)
        fb_title=$(echo "$fb_tab" | cut -d'|' -f3)
        echo "📘 Facebook: $fb_title"
        get_page_summary "$fb_id" "$fb_url"
    else
        echo "⚠️ Facebook 分頁未找到"
    fi
    
    # 監控 28Car
    car_tab=$(echo "$tabs" | grep "28car.com" | head -1)
    if [ -n "$car_tab" ]; then
        car_id=$(echo "$car_tab" | cut -d'|' -f1)
        car_url=$(echo "$car_tab" | cut -d'|' -f2)
        car_title=$(echo "$car_tab" | cut -d'|' -f3)
        echo "🚗 28Car: $car_title"
        get_page_summary "$car_id" "$car_url"
    else
        echo "⚠️ 28Car 分頁未找到"
    fi
    
    echo "=========================================="
    
    # 每 30 秒檢查一次
    sleep 30
done
