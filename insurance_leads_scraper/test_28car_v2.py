#!/usr/bin/env python3
"""
測試 28car.com - 帶完整 Headers
"""

from playwright.sync_api import sync_playwright
import time

URL = "https://www.28car.com/buycar.php?ct=0&cty=0&make=0&sort=insdate_d"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # 使用更真實的瀏覽器配置
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='zh-HK',
        timezone_id='Asia/Hong_Kong'
    )
    
    page = context.new_page()
    
    # 設置額外的 headers
    page.set_extra_http_headers({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    print("🌐 正在訪問 28car.com...")
    
    try:
        response = page.goto(URL, wait_until='domcontentloaded', timeout=30000)
        print(f"📄 狀態碼: {response.status if response else 'N/A'}")
        print(f"📄 頁面標題: {page.title()}")
        
        # 等待頁面加載
        time.sleep(5)
        
        html = page.content()
        print(f"\n📄 HTML 長度: {len(html)} 字符")
        print(f"📄 前 1000 字符:\n{html[:1000]}")
        
        # 檢查是否有車輛信息
        if 'selldetail' in html:
            print("\n✅ 找到車輛詳情鏈接!")
        
        # 查找表格
        tables = page.query_selector_all('table')
        print(f"\n📊 找到 {len(tables)} 個 table")
        
        # 查找行
        rows = page.query_selector_all('tr')
        print(f"📊 找到 {len(rows)} 個 tr")
        
        # 嘗試找到具體的車輛信息
        car_links = page.query_selector_all('a[href*="selldetail"]')
        print(f"🚗 找到 {len(car_links)} 個車輛鏈接")
        
        if car_links:
            print("\n📝 前 3 個車輛鏈接:")
            for link in car_links[:3]:
                href = link.get_attribute('href')
                text = link.inner_text().strip()[:50]
                print(f"   - {text} -> {href}")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    
    print("\n✅ 測試完成")
    browser.close()
