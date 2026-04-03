#!/usr/bin/env python3
"""
Facebook 登入工具 - 專門負責手動登入並儲存 Cookie/Storage State
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
import sys

STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
COOKIE_PATH = Path.home() / '.fb_crawler' / 'fb_cookies.json'

def main():
    print("="*60)
    print("📘 Facebook 登入工具")
    print("="*60)
    print(f"\n💾 登入狀態將保存到:")
    print(f"   Storage State: {STORAGE_STATE_PATH}")
    print(f"   Cookies: {COOKIE_PATH}\n")
    
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        print("🚀 啟動瀏覽器...")
        
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        
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
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-HK', 'zh', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            // 移除 webdriver 特性
            const originalDescriptor = Object.getOwnPropertyDescriptor(navigator, 'webdriver');
            if (originalDescriptor) {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
            }
        """)
        
        page = context.new_page()
        
        # 訪問 Facebook 登入頁
        print("🌐 訪問 Facebook 登入頁...")
        page.goto('https://www.facebook.com/login', wait_until='networkidle')
        
        print("\n" + "="*60)
        print("⏳ 請在瀏覽器中完成登入")
        print("="*60)
        print("\n步驟:")
        print("1. 輸入你的 Facebook 帳號密碼")
        print("2. 如有雙重驗證，請完成驗證")
        print("3. 登入成功後，回到呢度按 Enter\n")
        
        input("✅ 登入完成後，按 Enter 保存狀態...\n")
        
        # 確認已登入（檢查是否已離開登入頁）
        current_url = page.url
        if 'login' in current_url.lower():
            print("\n⚠️ 你仲喺登入頁，可能未成功登入")
            print("   請確認登入成功後再試一次")
            browser.close()
            sys.exit(1)
        
        # 等待一陣確保cookie穩定
        page.wait_for_timeout(2000)
        
        # 保存 Storage State（包含 Cookie + Local Storage）
        print("\n💾 保存 Storage State...")
        context.storage_state(path=str(STORAGE_STATE_PATH))
        print(f"   ✅ 已保存: {STORAGE_STATE_PATH}")
        
        # 單獨保存 Cookies（作為備份）
        print("💾 保存 Cookies...")
        cookies = context.cookies()
        import json
        with open(COOKIE_PATH, 'w') as f:
            json.dump(cookies, f)
        print(f"   ✅ 已保存: {COOKIE_PATH}")
        
        browser.close()
        
        print("\n" + "="*60)
        print("🎉 登入完成！")
        print("="*60)
        print(f"\n📍 登入狀態位置:")
        print(f"   {STORAGE_STATE_PATH}")
        print(f"\n👉 而家可以運行 scrape.py 了")

if __name__ == '__main__':
    main()
