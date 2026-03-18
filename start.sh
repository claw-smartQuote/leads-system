#!/bin/bash
# 啟動腳本

# 啟動虛擬環境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🚀 啟動汽車保險潛客系統..."
echo ""
echo "📋 系統資訊:"
echo "   表單網址: http://localhost:8000"
echo "   管理後台: http://localhost:8000/admin"
echo "   API 文檔: http://localhost:8000/docs"
echo ""
echo "⏹️  按 Ctrl+C 停止"
echo ""

# 啟動應用
python3 app.py