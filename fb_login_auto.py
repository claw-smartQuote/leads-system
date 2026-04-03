#!/usr/bin/env python3
"""
Facebook 登入工具 - 自動等待版
打開瀏覽器後，等待 120 秒讓你登入，然後自動保存狀態
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
import time

STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
WAIT_TIME = 120  # 等待 2 分鐘

def main():
    print("="*60)
    print("📘 Facebook 登入工具（自動保存版）")
    print("="*60)
    print(f"\n💾 登入狀態將保存到:")
    print(f"   {STORAGE_STATE_PATH}\n")
    
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        print("🚀 啟動瀏覽器...\n")
        
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-HK',
            timezone_id='Asia/Hong_Kong',
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        page = context.new_page()
        
        print("🌐 訪問 Facebook...")
        page.goto('https://www.facebook.com')
        
        print("\n" + "="*60)
        print("⏳ 請在瀏覽器中完成登入")
        print("="*60)
        print(f"\n⏰ 等待 {WAIT_TIME} 秒後自動保存...\n")
        
        # 倒計時
        for i in range(WAIT_TIME, 0, -1):
            print(f"\r⏱️  剩餘時間: {i} 秒   ", end='', flush=True)
            time.sleep(1)
            
            # 檢查是否已登入（檢查 URL 或頁面元素）
            try:
                if 'facebook.com' in page.url and page.url != 'https://www.facebook.com/':
                    # 已登入，提前保存
                    print(f"\n\n✅ 檢測到已登入！")
                    break
            except:
                pass
        
        print("\n\n💾 保存登入狀態...")
        context.storage_state(path=str(STORAGE_STATE_PATH))
        
        print("✅ 登入狀態已保存！")
        print(f"\n📍 保存位置: {STORAGE_STATE_PATH}")
        
        browser.close()
        
        print("\n🎉 完成！現在可以執行 FB 爬蟲了。")

if __name__ == '__main__':
    main()
