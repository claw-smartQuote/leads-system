#!/bin/bash
# 瀏覽器連接助手
# Browser Connection Helper

echo "🌐 瀏覽器連接助手"
echo "=================="
echo ""

# 檢查 openclaw CLI
if ! command -v openclaw &> /dev/null; then
    echo "❌ openclaw CLI 未找到"
    exit 1
fi

echo "📋 可用的瀏覽器配置檔:"
echo ""

# 1. openclaw 獨立瀏覽器（推薦，安全隔離）
echo "【選項 1: openclaw 獨立瀏覽器】⭐ 推薦"
echo "  • 完全隔離，不影響你的個人瀏覽器"
echo "  • 需要啟動專用 Chrome 實例"
echo "  • 命令: openclaw browser start --browser-profile openclaw"
echo ""

# 2. 連接現有 Chrome
echo "【選項 2: 連接現有 Chrome】"
echo "  • 使用你已開啟的 Chrome 標籤頁"
echo "  • 需要開啟 Chrome 遠程調試"
echo "  • 步驟:"
echo "    1. 在 Chrome 地址欄輸入: chrome://inspect/#remote-debugging"
echo "    2. 開啟 'Enable network target discovery'"
echo "    3. 點擊 'Open dedicated DevTools for node'"
echo "  • 命令: openclaw browser start --browser-profile user"
echo ""

# 3. 檢查當前狀態
echo "【檢查當前狀態】"
openclaw browser status 2>/dev/null || echo "  ℹ️  瀏覽器尚未啟動"
echo ""

# 詢問用戶選擇
echo "請選擇:"
echo "  1) 啟動獨立瀏覽器 (推薦)"
echo "  2) 連接現有 Chrome"
echo "  3) 檢查狀態"
echo "  q) 退出"
echo ""

read -p "選擇 (1/2/3/q): " CHOICE

case $CHOICE in
    1)
        echo "🚀 啟動獨立瀏覽器..."
        openclaw browser start --browser-profile openclaw
        echo "✅ 瀏覽器已啟動"
        echo "📱 現在可以查看標籤頁: openclaw browser tabs"
        ;;
    2)
        echo "🔗 嘗試連接現有 Chrome..."
        echo "⚠️  請確保 Chrome 已開啟遠程調試"
        openclaw browser start --browser-profile user
        ;;
    3)
        echo "🔍 檢查狀態..."
        openclaw browser status
        ;;
    q|Q)
        echo "👋 再見"
        exit 0
        ;;
    *)
        echo "❌ 無效選擇"
        exit 1
        ;;
esac

exit 0