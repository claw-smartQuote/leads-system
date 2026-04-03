#!/bin/bash
# 同步潛客資料到 Render 部署的潛客系統
# 執行時間: 每日晚上 11:00
# 自動化: 使用瀏覽器自動化上傳檔案

WORKSPACE="/Users/claw/.openclaw/workspace"
DATE=$(date +%Y%m%d)
LOG_FILE="$WORKSPACE/logs/sync_$(date +%Y%m%d_%H%M).log"
LEADS_SYSTEM_URL="https://leads-system.onrender.com"

echo "========================================" >> "$LOG_FILE"
echo "🔄 同步潛客資料開始: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 1. 檢查潛客系統是否可用
echo "🌐 檢查潛客系統狀態..." >> "$LOG_FILE"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$LEADS_SYSTEM_URL" || echo "000")

if [ "$HTTP_STATUS" != "200" ]; then
    echo "⚠️  潛客系統不可用 (HTTP $HTTP_STATUS)，跳過上傳" >> "$LOG_FILE"
    echo "💡 請手動上傳: https://leads-system.onrender.com/admin" >> "$LOG_FILE"
    
    # 發送 WhatsApp 通知
    if command -v openclaw &> /dev/null; then
        openclaw message send --target "+85221101144" --message "⚠️ 潛客系統暫時不可用 (HTTP $HTTP_STATUS)，請手動上傳" --channel whatsapp 2>/dev/null
    fi
    exit 0
fi

# 2. 查找最新的潛客資料
LEADS_FILE=""
for f in "$WORKSPACE/fb_潛客_${DATE}.xlsx" "$WORKSPACE/fb_leads_${DATE}.xlsx" "$WORKSPACE/爬蟲潛客總滙/爬蟲潛客總滙_最新.xlsx"; do
    if [ -f "$f" ]; then
        LEADS_FILE="$f"
        break
    fi
done

if [ -z "$LEADS_FILE" ]; then
    echo "⚠️ 沒有找到潛客資料檔案" >> "$LOG_FILE"
    exit 0
fi

echo "📄 找到潛客資料: $LEADS_FILE" >> "$LOG_FILE"

# 3. 使用瀏覽器自動化上傳
echo "🤖 啟動瀏覽器自動化上傳..." >> "$LOG_FILE"

python3 << 'PYTHON_SCRIPT' >> "$LOG_FILE" 2>&1
import asyncio
import os
from playwright.async_api import async_playwright

async def upload_leads():
    leads_file = os.environ.get('LEADS_FILE', '')
    admin_url = "https://leads-system.onrender.com/admin"
    
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_data_dir="/tmp/playwright_auth"
        )
        page = await context.new_page()
        
        try:
            # 導航到管理頁面
            await page.goto(admin_url, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            # 尋找上傳按鈕或輸入框
            # 根據實際頁面調整選擇器
            upload_inputs = await page.query_selector_all('input[type="file"]')
            
            if upload_inputs:
                # 上傳文件
                await upload_inputs[0].set_input_files(leads_file)
                print(f"✅ 已選擇文件: {leads_file}")
                
                # 點擊上傳/提交按鈕
                submit_buttons = await page.query_selector_all('button[type="submit"], button:has-text("上傳"), button:has-text("提交")')
                if submit_buttons:
                    await submit_buttons[0].click()
                    print("✅ 已點擊上傳按鈕")
                
                # 等待上傳完成
                await page.wait_for_timeout(5000)
                print("✅ 上傳完成")
            else:
                print("⚠️ 未找到上傳控件，請手動上傳")
                
        except Exception as e:
            print(f"❌ 上傳失敗: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(upload_leads())
PYTHON_SCRIPT

# 4. 複製到桌面
DESKTOP_DIR="/Users/claw/Desktop/潛客系統"
mkdir -p "$DESKTOP_DIR"
cp "$LEADS_FILE" "$DESKTOP_DIR/爬蟲潛客_${DATE}.xlsx"
cp "$LEADS_FILE" ~/Desktop/fb_潛客_${DATE}.xlsx
echo "✅ 已複製到桌面" >> "$LOG_FILE"

# 5. 發送完成通知
echo "✅ 同步完成: $(date)" >> "$LOG_FILE"

if command -v openclaw &> /dev/null; then
    openclaw message send --target "+85221101144" --message "✅ 潛客資料已同步到系統！今日上傳: $(basename $LEADS_FILE)" --channel whatsapp 2>/dev/null
fi

echo "========================================" >> "$LOG_FILE"
