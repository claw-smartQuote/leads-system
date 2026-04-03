#!/usr/bin/env python3
"""
Facebook 登入狀態保存腳本
用戶手動登入後，執行此腳本保存狀態
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json

STORAGE_STATE_PATH = Path.home() / '.fb_crawler' / 'fb_storage_state.json'

def save_login_state():
    """保存 Facebook 登入狀態"""
    print("🌐 啟動瀏覽器...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # 訪問 Facebook
        print("📘 訪問 Facebook...")
        page.goto('https://www.facebook.com', wait_until='networkidle')
        
        # 檢查是否已登入
        if 'login' not in page.url and 'facebook.com' in page.url:
            print("✅ 檢測到已登入狀態")
        else:
            print("⚠️  請在手動登入後按 Enter 繼續...")
            input()
        
        # 保存狀態
        STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(STORAGE_STATE_PATH))
        print(f"💾 登入狀態已保存: {STORAGE_STATE_PATH}")
        
        browser.close()
        print("✅ 完成！")

if __name__ == "__main__":
    save_login_state()
