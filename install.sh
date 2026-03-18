#!/bin/bash
# 安裝腳本

echo "🚀 安裝汽車保險潛客系統..."
echo ""

# 檢查 Python 版本
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ 請先安裝 Python 3.9+"
    exit 1
fi

# 創建虛擬環境（可選）
if [ ! -d "venv" ]; then
    echo "📦 創建虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
echo "🔄 啟動虛擬環境..."
source venv/bin/activate

# 安裝依賴
echo "📥 安裝依賴..."
pip install -r requirements.txt

# 創建必要的目錄
echo "📁 創建目錄..."
mkdir -p data exports static notifications

# 測試資料庫
echo "🧪 測試資料庫..."
python3 -c "from database import Database; db = Database(); print('✅ 資料庫測試成功')"

# 測試 Excel 匯出
echo "🧪 測試 Excel 匯出..."
python3 -c "from export_excel import ExcelExporter; e = ExcelExporter(); print('✅ Excel 模組測試成功')"

echo ""
echo "✅ 安裝完成！"
echo ""
echo "📝 啟動系統:"
echo "   ./start.sh"
echo ""
echo "🌐 啟動後訪問:"
echo "   表單: http://localhost:8000"
echo "   管理: http://localhost:8000/admin"