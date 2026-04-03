#!/usr/bin/env python3
"""
測試 28car.com 主頁
"""

from playwright.sync_api import sync_playwright
import time

URL = "https://www.28car.com"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("🌐 正在訪問 28car.com 主頁...")
    response = page.goto(URL, wait_until='domcontentloaded', timeout=30000)
    time.sleep(3)
    
    print(f"\n📄 狀態碼: {response.status if response else 'N/A'}")
    print(f"📄 頁面標題: {page.title()}")
    
    html = page.content()
    print(f"\n📄 頁面 HTML 前 3000 字符:\n{html[:3000]}")
    
    # 查找賣車鏈接
    sell_links = page.query_selector_all('a[href*="sell"], a[href*="buy"]')
    print(f"\n🔗 找到 {len(sell_links)} 個買賣車鏈接")
    for link in sell_links[:5]:
        href = link.get_attribute('href')
        text = link.inner_text().strip()
        if href:
            print(f"   - {text}: {href}")
    
    print("\n✅ 測試完成")
    browser.close()
