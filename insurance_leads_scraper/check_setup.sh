#!/bin/bash
# 系統設置檢查腳本

echo "=" * 60
echo "🔍 整合爬蟲系統 - 設置檢查"
echo "=" * 60

echo ""
echo "📁 工作目錄:"
ls -la /Users/claw/.openclaw/workspace/insurance_leads_scraper/

echo ""
echo "⏰ 定時任務狀態:"
launchctl list | grep com.insurance.scraper || echo "未找到定時任務"

echo ""
echo "📋 定時任務詳情:"
cat /Users/claw/Library/LaunchAgents/com.insurance.scraper.plist | grep -A2 "StartCalendarInterval"

echo ""
echo "📦 Python 依賴檢查:"
pip3 list | grep -E "pandas|playwright|undetected|openpyxl" || echo "部分依賴未安裝"

echo ""
echo "📂 輸出目錄:"
ls -la ~/Desktop/汽車保險潛客數據/ 2>/dev/null || echo "輸出目錄暫不存在"

echo ""
echo "=" * 60
echo "✅ 檢查完成"
echo "=" * 60
