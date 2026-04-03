#!/usr/bin/env python3
"""
調試 28car.com frame 結構
"""

import time
from playwright.sync_api import sync_playwright

URL = "https://www.28car.com/sell_lst.php"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("🌐 訪問頁面...")
    page.goto(URL, wait_until='networkidle', timeout=60000)
    
    print("⏳ 等待 10 秒...")
    time.sleep(10)
    
    print(f"\n🖼️  總共 {len(page.frames)} 個 frames:")
    
    for i, frame in enumerate(page.frames):
        url = frame.url
        print(f"\n   Frame {i}: {url}")
        
        try:
            html = frame.content()
            print(f"        HTML 長度: {len(html)}")
            
            if len(html) > 5000:
                # 檢查是否包含車輛信息
                if 'h_vid=' in html or 'sell_dsp' in html:
                    print(f"        ✅ 包含車輛信息!")
                
                # 檢查是否有表格
                tables = frame.query_selector_all('table')
                print(f"        📊 Tables: {len(tables)}")
                
                rows = frame.query_selector_all('tr')
                print(f"        📊 Rows: {len(rows)}")
                
        except Exception as e:
            print(f"        ❌ 錯誤: {e}")
    
    print("\n✅ 完成")
    time.sleep(3)
    browser.close()
