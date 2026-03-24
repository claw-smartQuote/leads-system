#!/usr/bin/env python3
"""
測試腳本 - 查看 28car.com 頁面結構
"""

from playwright.sync_api import sync_playwright
import time

URL = "https://www.28car.com/buycar.php?ct=0&cty=0&make=0&sort=insdate_d"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # 使用無頭模式
    page = browser.new_page()
    
    print("🌐 正在訪問 28car.com...")
    page.goto(URL, wait_until='domcontentloaded', timeout=30000)
    time.sleep(5)
    
    # 獲取頁面標題
    print(f"\n📄 頁面標題: {page.title()}")
    
    # 獲取頁面部分內容
    html = page.content()
    print(f"\n📄 頁面 HTML 前 2000 字符:\n{html[:2000]}")
    
    # 查找表格
    tables = page.query_selector_all('table')
    print(f"\n📊 找到 {len(tables)} 個 table 元素")
    
    # 查找所有行
    rows = page.query_selector_all('table tr')
    print(f"📊 找到 {len(rows)} 個 table tr 元素")
    
    # 嘗試其他選擇器
    divs = page.query_selector_all('div[class*="car"], div[class*="list"], div[class*="item"]')
    print(f"📦 找到 {len(divs)} 個可能包含車輛信息的 div")
    
    # 查找鏈接
    links = page.query_selector_all('a[href*="selldetail"]')
    print(f"🔗 找到 {len(links)} 個車輛詳情鏈接")
    
    # 檢查是否有 Cloudflare 或其他防護
    if 'cloudflare' in html.lower() or 'captcha' in html.lower():
        print("⚠️ 檢測到 Cloudflare 或驗證碼保護")
    
    if '28car' in html.lower():
        print("✅ 頁面包含 28car 內容")
    else:
        print("⚠️ 頁面內容似乎不包含 28car 內容")
    
    print("\n✅ 測試完成")
    browser.close()
