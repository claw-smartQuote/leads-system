#!/usr/bin/env python3
"""
Facebook 登入工具 - 保存登入狀態
執行後會打開瀏覽器，手動登入 Facebook
登入成功後，狀態會保存到 ~/.fb_crawler/fb_storage_state.json
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# 設定
STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'

def main():
    print("="*60)
    print("📘 Facebook 登入工具")
    print("="*60)
    print(f"\n💾 登入狀態將保存到:")
    print(f"   {STORAGE_STATE_PATH}\n")
    
    # 確保目錄存在
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        print("🚀 啟動瀏覽器...\n")
        
        # 啟動瀏覽器（非無頭模式）
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 創建上下文
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-HK',
            timezone_id='Asia/Hong_Kong',
        )
        
        # 隱藏自動化痕跡
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        page = context.new_page()
        
        # 訪問 Facebook
        print("🌐 訪問 Facebook...")
        page.goto('https://www.facebook.com')
        
        print("\n" + "="*60)
        print("⏳ 請在瀏覽器中完成登入")
        print("="*60)
        print("\n步驟:")
        print("1. 輸入你的 Facebook 帳號密碼")
        print("2. 完成登入")
        print("3. 登入成功後，回到這裡按 Enter\n")
        
        # 等待用戶操作
        input("✅ 登入完成後，按 Enter 保存狀態...\n")
        
        # 保存登入狀態
        print("\n💾 保存登入狀態...")
        context.storage_state(path=str(STORAGE_STATE_PATH))
        
        print("✅ 登入狀態已保存！")
        print(f"\n📍 保存位置: {STORAGE_STATE_PATH}")
        
        # 關閉瀏覽器
        browser.close()
        
        print("\n🎉 完成！現在可以執行 FB 爬蟲了。")
        print("   執行: python3 fb_crawler_final_v5.py")

if __name__ == '__main__':
    main()
