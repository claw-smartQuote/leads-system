#!/bin/bash
# 安裝腳本 - 設置每日自動爬蟲

echo "🚀 開始安裝整合爬蟲系統..."

# 1. 檢查並安裝必要的 Python 包
echo "📦 檢查 Python 依賴..."

pip3 install pandas openpyxl sqlite3 2>/dev/null || pip install pandas openpyxl sqlite3

# 檢查 Playwright
echo "  - Playwright"
pip3 show playwright > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "    正在安裝 Playwright..."
    pip3 install playwright
    python3 -m playwright install chromium
fi

# 檢查 undetected-chromedriver
echo "  - undetected-chromedriver"
pip3 show undetected-chromedriver > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "    正在安裝 undetected-chromedriver..."
    pip3 install undetected-chromedriver
fi

# 2. 創建日誌目錄
LOG_DIR="$HOME/.openclaw/workspace/insurance_leads_scraper/logs"
mkdir -p "$LOG_DIR"

# 3. 設置 Cron Job
echo "⏰ 配置定時任務..."

# 獲取當前用戶的 crontab
crontab -l > /tmp/current_cron 2>/dev/null || echo "# 新的 crontab" > /tmp/current_cron

# 檢查是否已存在
if grep -q "daily_scraper.py" /tmp/current_cron; then
    echo "  ℹ️ 定時任務已存在，跳過"
else
    # 添加新的定時任務（每天早上 9 點運行）
    echo "" >> /tmp/current_cron
    echo "# 汽車保險潛客爬蟲 - 每日自動執行" >> /tmp/current_cron
    echo "0 9 * * * cd $HOME/.openclaw/workspace/insurance_leads_scraper && /usr/bin/python3 daily_scraper.py >> $LOG_DIR/scraper_$(date +\%Y\%m\%d).log 2>&1" >> /tmp/current_cron
    
    # 應用 crontab
    crontab /tmp/current_cron
    echo "  ✅ 定時任務已添加（每天 9:00 執行）"
fi

# 4. 創建手動執行腳本
echo "📝 創建快速執行腳本..."

cat > "$HOME/.openclaw/workspace/insurance_leads_scraper/run_now.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 手動執行爬蟲..."
python3 daily_scraper.py
echo "✅ 執行完成"
EOF

chmod +x "$HOME/.openclaw/workspace/insurance_leads_scraper/run_now.sh"

# 5. 測試運行
echo ""
echo "🧪 是否要立即測試運行？(y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "🚀 開始測試運行..."
    python3 "$HOME/.openclaw/workspace/insurance_leads_scraper/daily_scraper.py"
fi

echo ""
echo "=" * 60
echo "✅ 安裝完成！"
echo "=" * 60
echo "📋 使用說明："
echo "   1. 自動執行: 每天 9:00 會自動運行"
echo "   2. 手動執行: ./run_now.sh"
echo "   3. 查看日誌: logs/ 目錄"
echo "   4. 輸出文件: ~/Desktop/汽車保險潛客數據/"
echo ""
echo "⚙️  管理定時任務:"
echo "   查看: crontab -l"
echo "   編輯: crontab -e"
echo "=" * 60
