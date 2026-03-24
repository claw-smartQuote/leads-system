#!/usr/bin/env python3
"""
最簡化測試 - 直接獲取 frame 文本
"""

import time
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    
    print("🌐 訪問 28car.com...")
    page.goto("https://www.28car.com/sell_lst.php", wait_until='domcontentloaded', timeout=60000)
    time.sleep(10)
    
    # 找內容 frame
    print("🔍 查找內容 frame...")
    for i, frame in enumerate(page.frames):
        try:
            url = frame.url
            if 'sell_lst' in url and '28car.com' in url:
                text = frame.inner_text('body')
                print(f"\nFrame {i}: {url[:60]}")
                print(f"  文本長度: {len(text)}")
                
                # 找電話號碼
                phones = re.findall(r'\d{4}[\s\-]?\d{4}', text)
                print(f"  找到 {len(phones)} 個電話號碼")
                if phones:
                    print(f"  示例: {phones[:5]}")
                
                # 找車型（通過常見品牌）
                brands = ['豐田', '寶馬', '本田', '日產', '平治', '凌志', '福士']
                found_brands = []
                for brand in brands:
                    if brand in text:
                        found_brands.append(brand)
                print(f"  找到品牌: {found_brands}")
                
        except Exception as e:
            print(f"Frame {i} 錯誤: {e}")
    
    print("\n✅ 完成")
    time.sleep(3)
    browser.close()
