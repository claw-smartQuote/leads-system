#!/usr/bin/env python3
"""
Facebook 自動登入腳本 (Playwright 版本)
"""

import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# 設定
STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'
CREDS_PATH = Path.home() / '.fb_crawler' / 'fb_credentials.json'

def load_credentials():
    """載入登入憑證"""
    if CREDS_PATH.exists():
        with open(CREDS_PATH, 'r') as f:
            return json.load(f)
    return None

def auto_login_fb():
    """自動登入 Facebook"""
    creds = load_credentials()
    
    if not creds:
        print("❌ 找不到憑證")
        return False
    
    print(f"🔑 找到憑證: {creds['email']}")
    
    print("\n🚀 啟動瀏覽器...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 需要可見瀏覽器
            args=['--disable-blink-features=AutomationControlled']
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
        """)
        
        page = context.new_page()
        
        print("🌐 訪問 Facebook...")
        page.goto('https://www.facebook.com', timeout=60000)
        page.wait_for_timeout(3000)
        
        # 填入電郵
        print("📝 填入電郵...")
        try:
            page.fill('#email', creds['email'])
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"⚠️ 填入電郵失敗: {e}")
        
        # 填入密碼
        print("📝 填入密碼...")
        try:
            page.fill('#pass', creds['password'])
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"⚠️ 填入密碼失敗: {e}")
        
        # 點擊登入
        print("🔘 點擊登入...")
        try:
            page.click('button[name="login"]')
        except:
            try:
                page.click('button[type="submit"]')
            except:
                print("⚠️ 找不到登入按鈕")
        
        print("⏳ 等待登入結果...")
        page.wait_for_timeout(8000)
        
        # 檢查 URL 是否改變（登入成功）
        if 'login' not in page.url.lower():
            print("✅ 登入成功！")
            
            # 保存登入狀態
            STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(STORAGE_STATE_PATH))
            
            print(f"✅ 登入狀態已保存: {STORAGE_STATE_PATH}")
            browser.close()
            return True
        else:
            print("❌ 登入失敗，可能需要處理驗證")
            print(f"   當前 URL: {page.url}")
            browser.close()
            return False

if __name__ == '__main__':
    success = auto_login_fb()
    if not success:
        print("\n⚠️ 自動登入失敗，請：")
        print("1. 運行: python3 fb_login.py")
        print("2. 手動完成登入")
        print("3. 回到瀏覽器按 Enter")
    sys.exit(0 if success else 1)
